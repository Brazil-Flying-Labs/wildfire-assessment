import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import AIAnalysisModal from "../ai/AIAnalysisModal";
import PrintReport from "../analysis-detail/PrintReport";
import BackButton from "../../components/BackButton";
import DateRangePicker from "../../components/DateRangePicker";
import { useLanguage } from "../../context/LanguageContext";
import { SEVERITY_COLORS, getSeverityTranslations, parseSeverityData } from "../../constants/severity";
import { formatLabel, formatAreaValue, formatPercentValue } from "../../utils/formatting";
import { downloadSeverityCsv } from "../../utils/csvExport";

const DAYS_BEFORE_AFTER_OPTIONS = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 20, 30, 45, 90];

const MOSAIC_STRATEGIES = [
  { value: "best_date_mosaic", labelKey: "app.mosaicBestDate" },
  { value: "best_date_masked_mosaic", labelKey: "app.mosaicBestDateMasked" },
  { value: "best_available_per_tile_mosaic", labelKey: "app.mosaicBestAvailable" },
  { value: "cloud_masked_light_mosaic", labelKey: "app.mosaicCloudMasked" },
];

function AnalysisPage({ authorizedFetch, baseUrl, onBack, onAnalysisComplete }) {
  const { t, language } = useLanguage();

  const [areasOfInterest, setAreasOfInterest] = useState([]);
  const [fetchState, setFetchState] = useState({ loading: true, error: null });
  const [selectedReserve, setSelectedReserve] = useState("");
  const [preFireInput, setPreFireInput] = useState("");
  const [postFireInput, setPostFireInput] = useState("");
  const [analysisResult, setAnalysisResult] = useState(null);
  const [analysisState, setAnalysisState] = useState({ loading: false, error: null });
  const [analysisStep, setAnalysisStep] = useState(0);
  const [roiOnly, setRoiOnly] = useState(false);
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [cloudThreshold, setCloudThreshold] = useState(100);
  const [daysBeforeAfter, setDaysBeforeAfter] = useState(30);
  const [mosaicStrategy, setMosaicStrategy] = useState("best_available_per_tile_mosaic");
  const [showMosaicInfo, setShowMosaicInfo] = useState(false);
  const analysisStepRef = useRef(null);
  const [hasResults, setHasResults] = useState(false);
  const [deliverableStatus, setDeliverableStatus] = useState({});
  const [backendAuthorizationError, setBackendAuthorizationError] = useState(false);
  const analyzeControllerRef = useRef(null);
  const deliverablePollRef = useRef({});
  const [reportAnalysis, setReportAnalysis] = useState(null);
  const [reportSummary, setReportSummary] = useState(null);
  const [reportLoading, setReportLoading] = useState(false);
  const [reportError, setReportError] = useState(null);

  const ensureAuthorizedResponse = useCallback(
    (response) => {
      if (response?.status === 403) {
        setBackendAuthorizationError(true);
        throw new Error(t("app.backendUnauthorized"));
      }
      return response;
    },
    [t]
  );

  const loadReserves = useCallback(() => {
    if (!baseUrl) {
      setFetchState({ loading: false, error: t("app.envNotConfigured") });
      return undefined;
    }

    const controller = new AbortController();
    setFetchState({ loading: true, error: null });

    (async () => {
      try {
        const response = await authorizedFetch(
          `${baseUrl}/area_of_interest/?page_size=999999999`,
          { signal: controller.signal }
        );

        ensureAuthorizedResponse(response);

        if (!response.ok) {
          throw new Error(t("app.errorLoadingReserves", { status: response.status }));
        }

        const data = await response.json();
        setAreasOfInterest(data.results || data);
        setFetchState({ loading: false, error: null });
      } catch (error) {
        if (error.name === "AbortError") return;
        console.error("Failed to fetch ecological reserves:", error);
        setFetchState({ loading: false, error: error.message });
      }
    })();

    return () => controller.abort();
  }, [authorizedFetch, baseUrl, ensureAuthorizedResponse, t]);

  useEffect(() => {
    const abort = loadReserves();
    return () => {
      if (typeof abort === "function") abort();
    };
  }, [loadReserves]);

  useEffect(() => {
    return () => {
      if (analyzeControllerRef.current) analyzeControllerRef.current.abort();
    };
  }, []);

  const hasError = Boolean(fetchState.error);

  const normalizeDateValue = useCallback((rawValue) => {
    if (!rawValue) return "";
    const trimmed = rawValue.trim();
    if (!trimmed) return "";
    if (/^\d{4}-\d{2}-\d{2}$/.test(trimmed)) return trimmed;
    const parsed = new Date(trimmed);
    if (Number.isNaN(parsed.getTime())) return "";
    return parsed.toISOString().slice(0, 10);
  }, []);

  const isIsoDate = useCallback(
    (value) => /^\d{4}-\d{2}-\d{2}$/.test(value || ""),
    []
  );

  const preFireDate = useMemo(
    () => (isIsoDate(preFireInput) ? preFireInput : ""),
    [preFireInput, isIsoDate]
  );

  const postFireDate = useMemo(
    () => (isIsoDate(postFireInput) ? postFireInput : ""),
    [postFireInput, isIsoDate]
  );

  const renderReserveOptions = () => {
    if (fetchState.loading) {
      return (
        <option value="" disabled>
          {t("app.loadingReserves")}
        </option>
      );
    }

    if (hasError) {
      return (
        <option value="" disabled>
          {fetchState.error}
        </option>
      );
    }

    if (!areasOfInterest.length) {
      return (
        <option value="" disabled>
          {t("app.noReserves")}
        </option>
      );
    }

    return [
      <option key="placeholder" value="" disabled>
        {t("app.chooseOption")}
      </option>,
      ...areasOfInterest.map((reserve) => (
        <option key={reserve.id} value={reserve.id}>
          {reserve.name}
        </option>
      )),
    ];
  };

  const isAnalyzeDisabled =
    fetchState.loading || hasError || analysisState.loading || !selectedReserve || !preFireDate || !postFireDate;

  const imageEntries = useMemo(() => {
    if (!analysisResult) return [];
    return Object.entries(analysisResult).filter(
      ([key, value]) => key.endsWith("_jpg") && typeof value === "string"
    );
  }, [analysisResult]);

  const tiffEntries = useMemo(() => {
    if (!analysisResult) return [];
    return Object.entries(analysisResult).filter(
      ([key, value]) => key.endsWith("_tif") && typeof value === "string"
    );
  }, [analysisResult]);

  const csvEntry = useMemo(() => {
    if (!analysisResult) return null;
    const entry = Object.entries(analysisResult).find(
      ([key, value]) => key.endsWith("_stats") && typeof value === "string"
    );
    return entry || null;
  }, [analysisResult]);

  const bestDates = useMemo(() => {
    if (!analysisResult) return null;
    const { pre_fire_best_date: preBest, post_fire_best_date: postBest } = analysisResult;
    const formattedPre = normalizeDateValue(preBest);
    const formattedPost = normalizeDateValue(postBest);
    if (!formattedPre && !formattedPost) return null;
    return { preBest: formattedPre, postBest: formattedPost };
  }, [analysisResult, normalizeDateValue]);

  const severityEntries = useMemo(() => {
    return parseSeverityData(analysisResult?.severity_map);
  }, [analysisResult]);

  const severityColorMap = SEVERITY_COLORS;

  const severityTranslationMap = useMemo(
    () => getSeverityTranslations(t),
    [t]
  );

  const handleDownloadSeverityCsv = useCallback(() => {
    downloadSeverityCsv(severityEntries);
  }, [severityEntries]);

  const scientificDeliverables = useMemo(
    () => [
      { label: "RGB pre-fire", value: "RGB_PRE_FIRE", urlKey: "scientific_rgb_pre_fire_url", taskKey: "scientific_rgb_pre_fire_task_id" },
      { label: "RGB post-fire", value: "RGB_POST_FIRE", urlKey: "scientific_rgb_post_fire_url", taskKey: "scientific_rgb_post_fire_task_id" },
      { label: "dNBR", value: "DNBR", urlKey: "scientific_dnbr_url", taskKey: "scientific_dnbr_task_id" },
      { label: "RBR", value: "RBR", urlKey: "scientific_rbr_url", taskKey: "scientific_rbr_task_id" },
      { label: "dNDVI", value: "DNDVI", urlKey: "scientific_dndvi_url", taskKey: "scientific_dndvi_task_id" },
    ],
    []
  );

  const isScientificDeliverableDisabled =
    fetchState.loading || hasError || !selectedReserve || !preFireDate || !postFireDate;

  const updateDeliverableStatus = useCallback((deliverableName, nextState) => {
    setDeliverableStatus((previous) => ({
      ...previous,
      [deliverableName]: {
        ...(previous[deliverableName] || {}),
        ...nextState,
      },
    }));
  }, []);

  const startDeliverablePolling = useCallback(
    (deliverableName, taskId, analysisRunId) => {
      if (deliverablePollRef.current[deliverableName]) {
        clearInterval(deliverablePollRef.current[deliverableName]);
      }

      const intervalId = setInterval(async () => {
        try {
          const params = new URLSearchParams({
            task_id: taskId,
            deliverable: deliverableName,
          });
          const url = `${baseUrl}/analysis_run/${analysisRunId}/task_status/?${params.toString()}`;
          const response = await authorizedFetch(url);
          if (!response.ok) return;

          const data = await response.json();

          if (data.state === "SUCCESS") {
            clearInterval(deliverablePollRef.current[deliverableName]);
            delete deliverablePollRef.current[deliverableName];
            updateDeliverableStatus(deliverableName, {
              polling: false,
              url: data.url || null,
            });
          } else if (data.state === "FAILURE") {
            clearInterval(deliverablePollRef.current[deliverableName]);
            delete deliverablePollRef.current[deliverableName];
            updateDeliverableStatus(deliverableName, {
              polling: false,
              error: data.error || t("app.deliverableError"),
            });
          }
        } catch {
          // Ignore polling errors, will retry on next interval
        }
      }, 5000);

      deliverablePollRef.current[deliverableName] = intervalId;
    },
    [authorizedFetch, baseUrl, updateDeliverableStatus, t]
  );

  // Cleanup polling intervals on unmount
  useEffect(() => {
    const intervals = deliverablePollRef.current;
    return () => {
      Object.values(intervals).forEach(clearInterval);
    };
  }, []);

  const handleScientificDeliverable = useCallback(
    async (deliverableName) => {
      if (isScientificDeliverableDisabled) return;

      updateDeliverableStatus(deliverableName, {
        loading: true,
        error: null,
        url: null,
      });

      try {
        if (!baseUrl) {
          throw new Error(t("app.apiNotConfigured"));
        }

        const queryParams = new URLSearchParams({
          pre_fire_date: preFireDate,
          post_fire_date: postFireDate,
          deliverable: deliverableName,
        });
        if (analysisResult?.analysis_run_id) {
          queryParams.set("analysis_run_id", analysisResult.analysis_run_id);
        }

        const url = `${baseUrl}/area_of_interest/${selectedReserve}/scientific_deliverable/?${queryParams.toString()}`;

        const response = await authorizedFetch(url, { method: "POST" });
        ensureAuthorizedResponse(response);

        if (!response.ok) {
          throw new Error(t("app.errorDeliverable", { status: response.status }));
        }

        const data = await response.json();
        updateDeliverableStatus(deliverableName, {
          loading: false,
          polling: true,
        });
        if (data.task_id && analysisResult?.analysis_run_id) {
          startDeliverablePolling(
            deliverableName,
            data.task_id,
            analysisResult.analysis_run_id
          );
        }
      } catch (error) {
        console.error("Failed to request scientific deliverable:", error);
        updateDeliverableStatus(deliverableName, {
          loading: false,
          error: error.message || "Unknown error",
        });
      }
    },
    [
      analysisResult,
      authorizedFetch,
      baseUrl,
      ensureAuthorizedResponse,
      isScientificDeliverableDisabled,
      preFireDate,
      postFireDate,
      selectedReserve,
      startDeliverablePolling,
      updateDeliverableStatus,
      t,
    ]
  );

  const analysisSteps = useMemo(
    () => [
      t("app.progressStep1"),
      t("app.progressStep2"),
      t("app.progressStep3"),
      t("app.progressStep4"),
      t("app.progressStep5"),
    ],
    [t]
  );

  const handleSubmit = async (event) => {
    event.preventDefault();

    if (isAnalyzeDisabled) return;

    if (!baseUrl) {
      setAnalysisState({ loading: false, error: t("app.apiNotConfigured") });
      return;
    }

    if (analyzeControllerRef.current) {
      analyzeControllerRef.current.abort();
    }

    const controller = new AbortController();
    analyzeControllerRef.current = controller;

    setAnalysisState({ loading: true, error: null });
    setAnalysisResult(null);
    setHasResults(false);
    setAnalysisStep(0);
    clearInterval(analysisStepRef.current);
    analysisStepRef.current = setInterval(() => {
      setAnalysisStep((prev) => (prev < 4 ? prev + 1 : prev));
    }, 6000);
    // Clear polling intervals and deliverable state
    Object.values(deliverablePollRef.current).forEach(clearInterval);
    deliverablePollRef.current = {};
    setDeliverableStatus({});

    try {
      const currentTheme = document.documentElement.getAttribute("data-theme") || "dark";
      const queryParams = new URLSearchParams({
        pre_fire_date: preFireDate,
        post_fire_date: postFireDate,
        roi_only: String(roiOnly),
        cloud_threshold: String(cloudThreshold),
        days_before_after: String(daysBeforeAfter),
        pre_fire_mosaic_strategy: mosaicStrategy,
        post_fire_mosaic_strategy: mosaicStrategy,
        roi_only_bg_color: currentTheme === "light" ? "white" : "black",
      });
      const url = `${baseUrl}/area_of_interest/${selectedReserve}/analyze/?${queryParams.toString()}`;

      const response = await authorizedFetch(url, {
        method: "POST",
        signal: controller.signal,
      });

      ensureAuthorizedResponse(response);

      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new Error(errorData?.error || t("app.errorAnalysis", { status: response.status }));
      }

      const data = await response.json();
      setAnalysisResult(data);
      setHasResults(true);
      setAnalysisState({ loading: false, error: null });
      if (onAnalysisComplete) onAnalysisComplete();
    } catch (error) {
      if (error.name === "AbortError") {
        if (analyzeControllerRef.current === controller) {
          setAnalysisState({ loading: false, error: null });
        }
        return;
      }

      console.error("Error during analysis:", error);
      setAnalysisState({ loading: false, error: error.message });
    } finally {
      clearInterval(analysisStepRef.current);
      setAnalysisStep(0);
      if (analyzeControllerRef.current === controller) {
        analyzeControllerRef.current = null;
      }
    }
  };

  // AI Analysis feature - memoized values
  const selectedReserveName = useMemo(() => {
    if (!selectedReserve || !areasOfInterest.length) return "";
    const reserve = areasOfInterest.find((r) => String(r.id) === String(selectedReserve));
    return reserve?.name || "";
  }, [selectedReserve, areasOfInterest]);

  const severityDistributionForAPI = useMemo(() => {
    if (!severityEntries.length) return {};
    return severityEntries.reduce((acc, { name, area, percent }) => {
      acc[name] = {
        area_ha: typeof area === "number" ? area : parseFloat(area) || 0,
        percent: typeof percent === "number" ? percent : parseFloat(percent) || 0,
      };
      return acc;
    }, {});
  }, [severityEntries]);

  // PrintReport data derived from the fetched analysis run
  const reportImageEntries = useMemo(() => {
    if (!reportAnalysis) return [];
    const items = [
      { label: t("analysisDetail.dnbr"), url: reportAnalysis.dnbr_url },
      { label: t("analysisDetail.rbr"), url: reportAnalysis.rbr_url },
      { label: t("analysisDetail.dndvi"), url: reportAnalysis.dndvi_url },
      { label: t("analysisDetail.preFireRgb"), url: reportAnalysis.rgb_pre_fire_url },
      { label: t("analysisDetail.postFireRgb"), url: reportAnalysis.rgb_post_fire_url },
    ];
    return items.filter((item) => item.url);
  }, [reportAnalysis, t]);

  const reportSeverityEntries = useMemo(() => {
    return parseSeverityData(reportAnalysis?.severity_data);
  }, [reportAnalysis]);

  const handlePrintReport = useCallback(async () => {
    const runId = analysisResult?.analysis_run_id;
    if (!runId || !baseUrl) return;

    setReportLoading(true);
    setReportError(null);

    try {
      // Fetch full analysis run (with provenance) if we haven't yet
      if (!reportAnalysis || reportAnalysis.id !== runId) {
        const runResponse = await authorizedFetch(`${baseUrl}/analysis_run/${runId}/`);
        if (!runResponse.ok) throw new Error(t("report.generateError"));
        const runData = await runResponse.json();
        setReportAnalysis(runData);
        if (runData.report_summary) {
          setReportSummary(runData.report_summary);
          setReportLoading(false);
          setTimeout(() => window.print(), 100);
          return;
        }
      } else if (reportSummary) {
        setReportLoading(false);
        window.print();
        return;
      }

      // Generate AI report summary
      const response = await authorizedFetch(
        `${baseUrl}/analysis_run/${runId}/report/`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ language }),
        }
      );

      if (!response.ok) throw new Error(t("report.generateError"));

      const data = await response.json();
      setReportSummary(data.report_summary);
      setTimeout(() => window.print(), 100);
    } catch (err) {
      console.error("Failed to generate report:", err);
      setReportError(err.message || t("report.generateError"));
    } finally {
      setReportLoading(false);
    }
  }, [analysisResult, baseUrl, authorizedFetch, reportAnalysis, reportSummary, language, t]);

  const handleRegenerate = useCallback(async () => {
    const runId = analysisResult?.analysis_run_id;
    if (!runId || !baseUrl) return;

    setReportLoading(true);
    setReportError(null);

    try {
      const response = await authorizedFetch(
        `${baseUrl}/analysis_run/${runId}/report/?regenerate=true`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ language }),
        }
      );

      if (!response.ok) throw new Error(t("report.generateError"));

      const data = await response.json();
      setReportSummary(data.report_summary);
    } catch (err) {
      console.error("Failed to regenerate report:", err);
      setReportError(err.message || t("report.generateError"));
    } finally {
      setReportLoading(false);
    }
  }, [analysisResult, baseUrl, authorizedFetch, language, t]);

  // Reset report state when a new analysis is run
  useEffect(() => {
    setReportAnalysis(null);
    setReportSummary(null);
    setReportError(null);
  }, [analysisResult?.analysis_run_id]);

  if (backendAuthorizationError) {
    return (
      <section className="app-main-content p-4 flex-grow-1">
        <div className="alert alert-warning" role="alert">
          {t("app.backendUnauthorized")}
        </div>
      </section>
    );
  }

  return (
    <>
      <section className="app-main-content analysis-page-content p-4 flex-grow-1">
        <div className="d-flex align-items-center justify-content-between mb-4 page-header-sticky">
          <h2 className="h4 mb-0">{t("app.analysisTitle")}</h2>
          <BackButton onClick={onBack} />
        </div>

        {/* Analysis Form Card */}
        <div className="card shadow-sm mb-4 no-print">
          <div className="card-header">
            <h3 className="h5 mb-0">{t("app.analysisParams")}</h3>
          </div>
          <div className="card-body">
            <form onSubmit={handleSubmit}>
              <div className="row g-3">
                <div className="col-12 col-lg-6">
                  <DateRangePicker
                    startDate={preFireDate}
                    endDate={postFireDate}
                    onRangeChange={(start, end) => {
                      setPreFireInput(start);
                      setPostFireInput(end);
                    }}
                    label={t("app.dateRange")}
                    startLabel={t("app.preFire")}
                    endLabel={t("app.postFire")}
                  />
                </div>

                <div className="col-12 col-md-6 col-lg-4">
                  <label htmlFor="reserve" className="form-label">
                    {t("app.selectArea")}
                  </label>
                  <select
                    className="form-select"
                    id="reserve"
                    name="reserve"
                    value={selectedReserve}
                    onChange={(event) => setSelectedReserve(event.target.value)}
                    disabled={fetchState.loading || hasError}
                  >
                    {renderReserveOptions()}
                  </select>
                  {hasError ? (
                    <div className="mt-2">
                      <p className="small text-danger mb-2">
                        {t("app.apiHint")}
                      </p>
                      <button
                        type="button"
                        className="btn btn-outline-danger btn-sm"
                        onClick={loadReserves}
                      >
                        {t("common.tryAgain")}
                      </button>
                    </div>
                  ) : null}
                </div>

                <div className="col-12 col-md-6 col-lg-2 d-flex align-items-end">
                  <button
                    type="submit"
                    className="btn btn-primary w-100"
                    disabled={isAnalyzeDisabled}
                  >
                    {analysisState.loading ? t("app.analyzing") : t("app.runAnalysis")}
                  </button>
                </div>
              </div>
              <div className="mt-3 pt-3 border-top">
                <div className="form-check">
                  <input
                    className="form-check-input"
                    type="checkbox"
                    id="roiOnly"
                    checked={roiOnly}
                    onChange={(e) => setRoiOnly(e.target.checked)}
                  />
                  <label className="form-check-label" htmlFor="roiOnly">
                    {t("app.roiOnly")}
                  </label>
                  <div className="form-text">{t("app.roiOnlyHint")}</div>
                </div>
              </div>
              <div className="mt-3 pt-3 border-top">
                <div
                  className="d-flex align-items-center gap-2 mb-0"
                  style={{ cursor: "pointer", color: "var(--bs-primary)", fontWeight: 600 }}
                  onClick={() => setAdvancedOpen(!advancedOpen)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") setAdvancedOpen(!advancedOpen); }}
                >
                  <svg
                    width="12" height="12" viewBox="0 0 12 12" fill="currentColor"
                    style={{ transform: advancedOpen ? "rotate(0deg)" : "rotate(-90deg)", transition: "transform 0.2s" }}
                  >
                    <path d="M2 4l4 4 4-4" />
                  </svg>
                  {t("app.advancedSettings")}
                </div>
                {advancedOpen ? (
                  <div className="mt-3 p-3 border rounded" style={{ background: "var(--card-bg, inherit)" }}>
                    <div className="row">
                      {/* Left column: Cloud threshold + Days */}
                      <div className="col-12 col-md-5">
                        <div className="mb-3">
                          <label htmlFor="cloudThreshold" className="form-label fw-semibold">
                            {t("app.cloudThreshold")}
                          </label>
                          <div className="d-flex align-items-center gap-2">
                            <input
                              type="range"
                              className="form-range flex-grow-1"
                              id="cloudThreshold"
                              min="0"
                              max="100"
                              value={cloudThreshold}
                              onChange={(e) => setCloudThreshold(Number(e.target.value))}
                            />
                            <span className="fw-semibold" style={{ minWidth: "48px", textAlign: "right", whiteSpace: "nowrap" }}>
                              {cloudThreshold}%
                            </span>
                          </div>
                          <div className="form-text">{t("app.cloudThresholdHint")}</div>
                        </div>
                        <div>
                          <label htmlFor="daysBeforeAfter" className="form-label fw-semibold">
                            {t("app.daysBeforeAfter")}
                          </label>
                          <div className="d-flex align-items-center gap-2">
                            <input
                              type="range"
                              className="form-range flex-grow-1"
                              id="daysBeforeAfter"
                              min="0"
                              max={DAYS_BEFORE_AFTER_OPTIONS.length - 1}
                              value={DAYS_BEFORE_AFTER_OPTIONS.indexOf(daysBeforeAfter)}
                              onChange={(e) => setDaysBeforeAfter(DAYS_BEFORE_AFTER_OPTIONS[Number(e.target.value)])}
                            />
                            <span className="fw-semibold" style={{ minWidth: "48px", textAlign: "right", whiteSpace: "nowrap" }}>
                              {daysBeforeAfter} {t("app.daysBeforeAfterSuffix")}
                            </span>
                          </div>
                          <div className="form-text">{t("app.daysBeforeAfterHint")}</div>
                        </div>
                      </div>
                      {/* Right column: Mosaic strategies */}
                      <div className="col-12 col-md-5 offset-md-2">
                        <div>
                          <label className="form-label fw-semibold">
                            {t("app.mosaicStrategy")}
                            <button
                              type="button"
                              className="btn btn-link btn-sm p-0 ms-1 align-baseline"
                              onClick={() => setShowMosaicInfo(true)}
                              title={t("app.mosaicStrategyInfo")}
                            >
                              <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <circle cx="12" cy="12" r="10" />
                                <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />
                                <line x1="12" y1="17" x2="12.01" y2="17" />
                              </svg>
                            </button>
                          </label>
                          {MOSAIC_STRATEGIES.map(({ value, labelKey }) => (
                            <div className="form-check" key={value}>
                              <input
                                className="form-check-input"
                                type="radio"
                                name="mosaicStrategy"
                                id={`mosaic-${value}`}
                                value={value}
                                checked={mosaicStrategy === value}
                                onChange={(e) => setMosaicStrategy(e.target.value)}
                              />
                              <label className="form-check-label" htmlFor={`mosaic-${value}`}>
                                {t(labelKey)}
                              </label>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                ) : null}
              </div>
            </form>
          </div>
        </div>

        {/* Analysis Progress */}
        {analysisState.loading ? (
          <div className="card shadow-sm">
            <div className="card-body p-4">
              <div className="analysis-progress-bar mb-4">
                <div
                  className="analysis-progress-bar__fill"
                  style={{ width: `${((analysisStep + 1) / analysisSteps.length) * 100}%` }}
                />
              </div>
              <div className="d-flex flex-column gap-2">
                {analysisSteps.map((label, i) => (
                  <div
                    key={i}
                    className={`analysis-step ${
                      i < analysisStep
                        ? "analysis-step--completed"
                        : i === analysisStep
                          ? "analysis-step--active"
                          : "analysis-step--pending"
                    }`}
                  >
                    <span className="analysis-step__icon">
                      {i < analysisStep ? (
                        <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                          <path d="M13.485 3.929a1 1 0 0 1 .086 1.406l-6 7a1 1 0 0 1-1.48.055l-3-3a1 1 0 0 1 1.41-1.42l2.216 2.217 5.338-6.214a1 1 0 0 1 1.43-.044Z" />
                        </svg>
                      ) : i === analysisStep ? (
                        <div className="spinner-border spinner-border-sm" role="status">
                          <span className="visually-hidden">{t("common.loading")}</span>
                        </div>
                      ) : (
                        <span className="analysis-step__dot" />
                      )}
                    </span>
                    <span className="analysis-step__label">{label}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : null}

        {/* Analysis Error */}
        {!analysisState.loading && analysisState.error ? (
          <div className="alert alert-danger" role="alert">
            {analysisState.error}
          </div>
        ) : null}

        {/* Analysis Results */}
        {!analysisState.loading && !analysisState.error && hasResults && analysisResult ? (
          <div className="analysis-results d-flex flex-column gap-4">
            <div className="d-flex justify-content-end no-print">
              {analysisResult?.analysis_run_id && (
                <button
                  type="button"
                  className="btn btn-outline-secondary btn-sm d-flex align-items-center gap-1 btn-print-report"
                  onClick={handlePrintReport}
                  disabled={reportLoading}
                  title={t("common.printReport")}
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                    <polyline points="14 2 14 8 20 8" />
                    <line x1="16" y1="13" x2="8" y2="13" />
                    <line x1="16" y1="17" x2="8" y2="17" />
                  </svg>
                  {t("common.printReport")}
                </button>
              )}
            </div>

            {/* Best Dates */}
            {bestDates ? (
              <div className="card shadow-sm">
                <div className="card-header d-flex align-items-center justify-content-between">
                  <h3 className="h5 mb-0">{t("app.bestDates")}</h3>
                  <button
                    type="button"
                    className="btn btn-outline-primary btn-sm"
                    onClick={() => {
                      if (bestDates.preBest) setPreFireInput(bestDates.preBest);
                      if (bestDates.postBest) setPostFireInput(bestDates.postBest);
                    }}
                  >
                    {t("app.useBestDates")}
                  </button>
                </div>
                <div className="card-body">
                  <dl className="row mb-0">
                    {bestDates.preBest ? (
                      <>
                        <dt className="text-muted small col-sm-4">{t("app.preFire")}</dt>
                        <dd className="col-sm-8 mb-2">{bestDates.preBest}</dd>
                      </>
                    ) : null}
                    {bestDates.postBest ? (
                      <>
                        <dt className="text-muted small col-sm-4">{t("app.postFire")}</dt>
                        <dd className="col-sm-8 mb-0">{bestDates.postBest}</dd>
                      </>
                    ) : null}
                  </dl>
                </div>
              </div>
            ) : null}

            {/* Severity Table */}
            {severityEntries.length ? (
              <div className="card shadow-sm">
                <div className="card-header d-flex align-items-center justify-content-between">
                  <h3 className="h5 mb-0">{t("app.severityTitle")}</h3>
                  <button
                    type="button"
                    className="btn btn-outline-secondary btn-sm d-flex align-items-center gap-1"
                    onClick={handleDownloadSeverityCsv}
                    title={t("common.downloadCsv")}
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                      <polyline points="7 10 12 15 17 10" />
                      <line x1="12" y1="15" x2="12" y2="3" />
                    </svg>
                    CSV
                  </button>
                </div>
                <div className="card-body">
                  <div className="table-responsive">
                    <table className="table table-hover mb-0">
                      <thead className="table-light">
                        <tr>
                          <th scope="col">{t("app.severity")}</th>
                          <th scope="col">{t("app.areaHa")}</th>
                          <th scope="col">{t("app.percent")}</th>
                        </tr>
                      </thead>
                      <tbody>
                        {severityEntries.map(({ name, area, percent }) => (
                          <tr key={name}>
                            <td>
                              <span className="d-flex align-items-center gap-2">
                                {severityColorMap[name] && (
                                  <span
                                    className="d-inline-block rounded severity-color"
                                    style={{
                                      width: "12px",
                                      height: "12px",
                                      backgroundColor: severityColorMap[name],
                                    }}
                                  />
                                )}
                                {severityTranslationMap[name] || name}
                              </span>
                            </td>
                            <td>{formatAreaValue(area)}</td>
                            <td>{formatPercentValue(percent)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            ) : null}

            {/* Visualizations */}
            {imageEntries.length ? (
              <div className="card shadow-sm">
                <div className="card-header">
                  <h3 className="h5 mb-0">{t("app.visualizations")}</h3>
                </div>
                <div className="card-body">
                  <div className="row g-3">
                    {imageEntries.map(([key, url]) => (
                      <div className="col-md-6 col-lg-4" key={key}>
                        <div className="text-center">
                          <div className="fw-semibold mb-2">{formatLabel(key)}</div>
                          <a href={url} target="_blank" rel="noopener noreferrer">
                            <img
                              src={url}
                              alt={formatLabel(key)}
                              className="img-fluid rounded border"
                              style={{ maxHeight: "300px" }}
                              loading="lazy"
                            />
                          </a>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ) : null}

            {/* Downloads */}
            {tiffEntries.length || csvEntry ? (
              <div className="card shadow-sm no-print">
                <div className="card-header">
                  <h3 className="h5 mb-0">{t("app.downloads")}</h3>
                </div>
                <div className="card-body">
                  <div className="d-flex flex-wrap gap-2">
                    {tiffEntries.map(([key, url]) => (
                      <a
                        key={key}
                        href={url}
                        className="btn btn-outline-secondary btn-sm"
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        {formatLabel(key)} (TIFF)
                      </a>
                    ))}
                    {csvEntry ? (
                      <a
                        href={csvEntry[1]}
                        className="btn btn-outline-secondary btn-sm"
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        {formatLabel(csvEntry[0])} (CSV)
                      </a>
                    ) : null}
                  </div>
                </div>
              </div>
            ) : null}

            {/* Scientific Deliverables */}
            <div className="card shadow-sm no-print">
              <div className="card-header">
                <h3 className="h5 mb-0">{t("app.deliverableTitle")}</h3>
              </div>
              <div className="card-body">
                <p className="small text-muted mb-3">
                  {t("app.deliverableHint")}
                </p>
                <div className="d-flex flex-wrap gap-3">
                  {scientificDeliverables.map(({ label, value }) => {
                    const status = deliverableStatus[value] || {};
                    const deliverableUrl = status.url;
                    const isProcessing = status.loading || status.polling;
                    const cardClass = deliverableUrl
                      ? "is-ready"
                      : isProcessing
                        ? "is-processing"
                        : status.error
                          ? "is-error"
                          : "";

                    return (
                      <div
                        key={value}
                        className={`card shadow-sm deliverable-card ${cardClass}`}
                      >
                        <div className="card-body py-3 px-3">
                          <div className="fw-semibold small mb-2">{label}</div>
                          {deliverableUrl ? (
                            <a
                              href={deliverableUrl}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="btn btn-sm btn-outline-success d-inline-flex align-items-center gap-1"
                            >
                              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
                                <polyline points="15 3 21 3 21 9" />
                                <line x1="10" y1="14" x2="21" y2="3" />
                              </svg>
                              {t("app.deliverableOpen")}
                            </a>
                          ) : isProcessing ? (
                            <div className="d-flex align-items-center gap-2 text-muted small">
                              <div className="spinner-border spinner-border-sm" role="status">
                                <span className="visually-hidden">{t("common.loading")}</span>
                              </div>
                              {t("app.deliverableProcessing")}
                            </div>
                          ) : status.error ? (
                            <div>
                              <div className="small text-danger mb-1">{status.error}</div>
                              <button
                                type="button"
                                className="btn btn-sm btn-outline-secondary"
                                disabled={isScientificDeliverableDisabled}
                                onClick={() => handleScientificDeliverable(value)}
                              >
                                {t("common.tryAgain")}
                              </button>
                            </div>
                          ) : (
                            <button
                              type="button"
                              className="btn btn-sm btn-outline-primary"
                              disabled={isScientificDeliverableDisabled}
                              onClick={() => handleScientificDeliverable(value)}
                              title={t("app.deliverableTooltip", { label })}
                            >
                              {t("app.deliverableRequest")}
                            </button>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          </div>
        ) : null}

        {/* Empty State */}
        {!analysisState.loading && !analysisState.error && !analysisResult ? (
          <div className="placeholder-card border border-dashed rounded-3 p-5 text-center text-muted bg-white">
            <p className="mb-0">{t("app.selectParamsHint")}</p>
          </div>
        ) : null}
      </section>

      <AIAnalysisModal
        isVisible={hasResults && severityEntries.length > 0}
        preFireDate={preFireDate}
        postFireDate={postFireDate}
        areaOfInterest={selectedReserveName}
        severityDistribution={severityDistributionForAPI}
        imageUrls={imageEntries.map(([key, url]) => ({ label: formatLabel(key), url }))}
        authorizedFetch={authorizedFetch}
        baseUrl={baseUrl}
      />

      {reportLoading && (
        <div className="position-fixed top-0 start-0 w-100 h-100 d-flex justify-content-center align-items-center no-print"
          style={{ backgroundColor: "rgba(0,0,0,0.5)", zIndex: 9999 }}>
          <div className="bg-white rounded p-4 text-center shadow">
            <div className="spinner-border text-primary mb-3" role="status">
              <span className="visually-hidden">{t("common.loading")}</span>
            </div>
            <p className="mb-0">{t("report.generating")}</p>
          </div>
        </div>
      )}

      {reportError && (
        <div className="alert alert-danger alert-dismissible fade show position-fixed bottom-0 end-0 m-3 no-print" style={{ zIndex: 9999 }} role="alert">
          {reportError}
          <button type="button" className="btn-close" onClick={() => setReportError(null)} />
        </div>
      )}

      {reportAnalysis && (
        <PrintReport
          analysis={reportAnalysis}
          severityEntries={reportSeverityEntries}
          imageEntries={reportImageEntries}
          reportSummary={reportSummary}
          reportLoading={reportLoading}
          onRegenerate={handleRegenerate}
          t={t}
        />
      )}

      {showMosaicInfo && (
        <div className="modal d-block" tabIndex="-1" style={{ backgroundColor: "rgba(0,0,0,0.5)", zIndex: 1200 }} onClick={() => setShowMosaicInfo(false)}>
          <div className="modal-dialog modal-dialog-scrollable modal-dialog-centered" style={{ width: "90%", maxWidth: "600px", margin: "0 auto", maxHeight: "70vh" }} onClick={(e) => e.stopPropagation()}>
            <div className="modal-content" style={{ maxHeight: "70vh" }}>
              <div className="modal-header">
                <h5 className="modal-title">{t("app.mosaicStrategyInfo")}</h5>
                <button type="button" className="btn-close" onClick={() => setShowMosaicInfo(false)} />
              </div>
              <div className="modal-body">
                <p>{t("mosaic.intro")}</p>
                <p>{t("mosaic.differencePoints")}</p>
                <ul>
                  <li>{t("mosaic.point1")}</li>
                  <li>{t("mosaic.point2")}</li>
                  <li>{t("mosaic.point3")}</li>
                </ul>

                <h6 className="fw-bold mt-4">{t("app.mosaicBestDate")}</h6>
                <p>{t("mosaic.bestDate.description")}</p>
                <ul>
                  <li><strong>{t("mosaic.characteristics")}:</strong> {t("mosaic.bestDate.characteristics")}</li>
                  <li><strong>{t("mosaic.advantage")}:</strong> {t("mosaic.bestDate.advantage")}</li>
                  <li><strong>{t("mosaic.limitation")}:</strong> {t("mosaic.bestDate.limitation")}</li>
                </ul>

                <h6 className="fw-bold mt-4">{t("app.mosaicBestDateMasked")}</h6>
                <p>{t("mosaic.bestDateMasked.description")}</p>
                <ul>
                  <li><strong>{t("mosaic.characteristics")}:</strong> {t("mosaic.bestDateMasked.characteristics")}</li>
                  <li><strong>{t("mosaic.advantage")}:</strong> {t("mosaic.bestDateMasked.advantage")}</li>
                  <li><strong>{t("mosaic.limitation")}:</strong> {t("mosaic.bestDateMasked.limitation")}</li>
                </ul>

                <h6 className="fw-bold mt-4">{t("app.mosaicBestAvailable")}</h6>
                <p>{t("mosaic.bestAvailable.description")}</p>
                <ul>
                  <li><strong>{t("mosaic.characteristics")}:</strong> {t("mosaic.bestAvailable.characteristics")}</li>
                  <li><strong>{t("mosaic.advantage")}:</strong> {t("mosaic.bestAvailable.advantage")}</li>
                  <li><strong>{t("mosaic.limitation")}:</strong> {t("mosaic.bestAvailable.limitation")}</li>
                </ul>

                <h6 className="fw-bold mt-4">{t("app.mosaicCloudMasked")}</h6>
                <p>{t("mosaic.cloudMasked.description")}</p>
                <ul>
                  <li><strong>{t("mosaic.characteristics")}:</strong> {t("mosaic.cloudMasked.characteristics")}</li>
                  <li><strong>{t("mosaic.advantage")}:</strong> {t("mosaic.cloudMasked.advantage")}</li>
                  <li><strong>{t("mosaic.limitation")}:</strong> {t("mosaic.cloudMasked.limitation")}</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

export default AnalysisPage;
