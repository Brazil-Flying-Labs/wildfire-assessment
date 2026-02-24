import { useCallback, useEffect, useRef, useState, useMemo } from "react";
import AIAnalysisModal from "../ai/AIAnalysisModal";
import BackButton from "../../components/BackButton";
import { useLanguage } from "../../context/LanguageContext";
import { formatDate, formatDateTime, formatNumber } from "../../utils/formatting";
import { SEVERITY_COLORS, getSeverityTranslations, parseSeverityData } from "../../constants/severity";
import { downloadSeverityCsv } from "../../utils/csvExport";
import SeverityTable from "./SeverityTable";
import ImageGallery from "./ImageGallery";
import ScientificDeliverables from "./ScientificDeliverables";

function AnalysisDetail({ authorizedFetch, baseUrl, analysisId, onBack, onNotificationsRead, scrollToDeliverable }) {
  const { t } = useLanguage();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [deliverableStatus, setDeliverableStatus] = useState({});
  const pollIntervalsRef = useRef({});
  const deliverablesRef = useRef(null);

  const loadAnalysis = useCallback(async () => {
    if (!baseUrl || !analysisId) return;

    setLoading(true);
    setError(null);

    try {
      const response = await authorizedFetch(`${baseUrl}/analysis_run/${analysisId}/`);
      if (response.ok) {
        const data = await response.json();
        setAnalysis(data);
      } else {
        throw new Error(t("analysisDetail.errorLoading"));
      }
    } catch (err) {
      console.error("Error loading analysis:", err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [authorizedFetch, baseUrl, analysisId, t]);

  useEffect(() => {
    loadAnalysis();
  }, [loadAnalysis]);

  // Auto-mark notifications as read for this analysis
  useEffect(() => {
    if (!baseUrl || !analysisId) return;
    authorizedFetch(`${baseUrl}/notifications/mark-read/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ analysis_run_id: analysisId }),
    })
      .then((response) => {
        if (response.ok && onNotificationsRead) onNotificationsRead();
      })
      .catch(() => {});
  }, [authorizedFetch, baseUrl, analysisId, onNotificationsRead]);

  // Scroll to deliverables section when navigating from a notification
  useEffect(() => {
    if (scrollToDeliverable && !loading && analysis && deliverablesRef.current) {
      deliverablesRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [scrollToDeliverable, loading, analysis]);

  const imageEntries = useMemo(() => {
    if (!analysis) return [];
    const items = [
      { label: t("analysisDetail.dnbr"), url: analysis.dnbr_url },
      { label: t("analysisDetail.rbr"), url: analysis.rbr_url },
      { label: t("analysisDetail.dndvi"), url: analysis.dndvi_url },
      { label: t("analysisDetail.preFireRgb"), url: analysis.rgb_pre_fire_url },
      { label: t("analysisDetail.postFireRgb"), url: analysis.rgb_post_fire_url },
    ];
    return items.filter((item) => item.url);
  }, [analysis, t]);

  const severityTranslationMap = useMemo(() => getSeverityTranslations(t), [t]);

  const severityEntries = useMemo(() => {
    return parseSeverityData(analysis?.severity_data);
  }, [analysis]);

  const severityDistributionForAPI = useMemo(() => {
    const result = {};
    for (const { name, area, percent } of severityEntries) {
      result[name] = { area_ha: area, percent };
    }
    return result;
  }, [severityEntries]);

  const handleDownloadSeverityCsv = useCallback(() => {
    downloadSeverityCsv(severityEntries);
  }, [severityEntries]);

  const scientificDeliverables = useMemo(
    () => [
      { label: "dNBR", value: "DNBR", urlKey: "scientific_dnbr_url", taskKey: "scientific_dnbr_task_id" },
      { label: "RBR", value: "RBR", urlKey: "scientific_rbr_url", taskKey: "scientific_rbr_task_id" },
      { label: "dNDVI", value: "DNDVI", urlKey: "scientific_dndvi_url", taskKey: "scientific_dndvi_task_id" },
      { label: "RGB Pre-fire", value: "RGB_PRE_FIRE", urlKey: "scientific_rgb_pre_fire_url", taskKey: "scientific_rgb_pre_fire_task_id" },
      { label: "RGB Post-fire", value: "RGB_POST_FIRE", urlKey: "scientific_rgb_post_fire_url", taskKey: "scientific_rgb_post_fire_task_id" },
    ],
    []
  );

  const startPolling = useCallback(
    (deliverableName, taskId) => {
      if (pollIntervalsRef.current[deliverableName]) {
        clearInterval(pollIntervalsRef.current[deliverableName]);
      }

      const intervalId = setInterval(async () => {
        try {
          const params = new URLSearchParams({
            task_id: taskId,
            deliverable: deliverableName,
          });
          const url = `${baseUrl}/analysis_run/${analysis.id}/task_status/?${params.toString()}`;
          const response = await authorizedFetch(url);
          if (!response.ok) return;

          const data = await response.json();

          if (data.state === "SUCCESS") {
            clearInterval(pollIntervalsRef.current[deliverableName]);
            delete pollIntervalsRef.current[deliverableName];
            setDeliverableStatus((prev) => ({
              ...prev,
              [deliverableName]: { polling: false },
            }));
            loadAnalysis();
          } else if (data.state === "FAILURE") {
            clearInterval(pollIntervalsRef.current[deliverableName]);
            delete pollIntervalsRef.current[deliverableName];
            setDeliverableStatus((prev) => ({
              ...prev,
              [deliverableName]: {
                polling: false,
                error: data.error || t("app.deliverableError"),
              },
            }));
          }
        } catch {
          // Ignore polling errors, will retry on next interval
        }
      }, 5000);

      pollIntervalsRef.current[deliverableName] = intervalId;
    },
    [analysis, authorizedFetch, baseUrl, loadAnalysis, t]
  );

  useEffect(() => {
    if (!analysis) return;
    for (const { value, urlKey, taskKey } of scientificDeliverables) {
      const hasUrl = analysis[urlKey];
      const taskId = analysis[taskKey];
      if (!hasUrl && taskId && !pollIntervalsRef.current[value]) {
        setDeliverableStatus((prev) => ({
          ...prev,
          [value]: { polling: true },
        }));
        startPolling(value, taskId);
      }
    }
  }, [analysis, scientificDeliverables, startPolling]);

  useEffect(() => {
    const intervals = pollIntervalsRef.current;
    return () => {
      Object.values(intervals).forEach(clearInterval);
    };
  }, []);

  const handleScientificDeliverable = useCallback(
    async (deliverableName) => {
      if (!analysis) return;

      setDeliverableStatus((prev) => ({
        ...prev,
        [deliverableName]: { loading: true, error: null },
      }));

      try {
        const queryParams = new URLSearchParams({
          pre_fire_date: analysis.pre_fire_date,
          post_fire_date: analysis.post_fire_date,
          deliverable: deliverableName,
          analysis_run_id: analysis.id,
        });

        const url = `${baseUrl}/area_of_interest/${analysis.area_of_interest}/scientific_deliverable/?${queryParams.toString()}`;
        const response = await authorizedFetch(url, { method: "POST" });

        if (!response.ok) {
          throw new Error(t("app.errorDeliverable", { status: response.status }));
        }

        const data = await response.json();
        setDeliverableStatus((prev) => ({
          ...prev,
          [deliverableName]: { loading: false, polling: true },
        }));
        if (data.task_id) {
          startPolling(deliverableName, data.task_id);
        }
      } catch (err) {
        console.error("Failed to request scientific deliverable:", err);
        setDeliverableStatus((prev) => ({
          ...prev,
          [deliverableName]: { loading: false, error: err.message },
        }));
      }
    },
    [analysis, authorizedFetch, baseUrl, startPolling, t]
  );

  if (loading) {
    return (
      <div className="d-flex justify-content-center align-items-center p-5">
        <div className="spinner-border text-primary" role="status">
          <span className="visually-hidden">{t("common.loading")}</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4">
        <div className="alert alert-danger" role="alert">
          {error}
          <button
            type="button"
            className="btn btn-outline-danger btn-sm ms-3"
            onClick={loadAnalysis}
          >
            {t("common.tryAgain")}
          </button>
        </div>
        <BackButton onClick={onBack} className="" />
      </div>
    );
  }

  return (
    <>
    <div className="analysis-detail p-4">
      <div className="d-flex align-items-center justify-content-between mb-4 page-header-sticky">
        <h2 className="h4 mb-0">{t("analysisDetail.title")}</h2>
        <div className="d-flex align-items-center gap-2">
          <button
            type="button"
            className="btn btn-outline-secondary btn-sm d-flex align-items-center gap-1 no-print"
            onClick={() => window.print()}
            title={t("common.print")}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="6 9 6 2 18 2 18 9" />
              <path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2" />
              <rect x="6" y="14" width="12" height="8" />
            </svg>
            {t("common.print")}
          </button>
          <BackButton onClick={onBack} />
        </div>
      </div>

      {/* Analysis Info Card */}
      <div className="card shadow-sm mb-4">
        <div className="card-header">
          <h3 className="h5 mb-0">{analysis?.area_name}</h3>
        </div>
        <div className="card-body">
          <div className="row g-3">
            <div className="col-md-6">
              <dl className="mb-0">
                <dt className="text-muted small">{t("analysisDetail.country")}</dt>
                <dd className="mb-3">{analysis?.country_name || "-"}</dd>

                <dt className="text-muted small">{t("analysisDetail.preFireDate")}</dt>
                <dd className="mb-3">{formatDate(analysis?.pre_fire_date)}</dd>

                <dt className="text-muted small">{t("analysisDetail.postFireDate")}</dt>
                <dd className="mb-3">{formatDate(analysis?.post_fire_date)}</dd>
              </dl>
            </div>
            <div className="col-md-6">
              <dl className="mb-0">
                <dt className="text-muted small">{t("analysisDetail.totalBurned")}</dt>
                <dd className="mb-3">
                  <span className="h4 text-danger">{formatNumber(analysis?.total_burned_ha)}</span>
                  <span className="text-muted ms-1">ha</span>
                </dd>

                <dt className="text-muted small">{t("analysisDetail.status")}</dt>
                <dd className="mb-3">
                  <span className={`badge ${analysis?.status === 'completed' ? 'bg-success' : 'bg-secondary'}`}>
                    {analysis?.status}
                  </span>
                </dd>

                <dt className="text-muted small">{t("analysisDetail.runDate")}</dt>
                <dd className="mb-0">{formatDateTime(analysis?.created_at)}</dd>
              </dl>
            </div>
          </div>
        </div>
      </div>

      <SeverityTable
        severityEntries={severityEntries}
        severityColorMap={SEVERITY_COLORS}
        severityTranslationMap={severityTranslationMap}
        onDownloadCsv={handleDownloadSeverityCsv}
        t={t}
      />

      <ImageGallery imageEntries={imageEntries} t={t} />

      <ScientificDeliverables
        ref={deliverablesRef}
        analysis={analysis}
        scientificDeliverables={scientificDeliverables}
        deliverableStatus={deliverableStatus}
        onRequest={handleScientificDeliverable}
        t={t}
      />

      {/* Raw Data */}
      <div className="card shadow-sm no-print">
        <div className="card-header">
          <h3 className="h5 mb-0">{t("analysisDetail.rawData")}</h3>
        </div>
        <div className="card-body">
          <details>
            <summary className="fw-medium mb-2">{t("analysisDetail.viewJson")}</summary>
            <pre className="mb-0 bg-light p-3 rounded overflow-auto" style={{ maxHeight: '300px' }}>
              {JSON.stringify(analysis, null, 2)}
            </pre>
          </details>
        </div>
      </div>
    </div>

    <AIAnalysisModal
      isVisible={!!analysis && severityEntries.length > 0}
      preFireDate={analysis?.pre_fire_date}
      postFireDate={analysis?.post_fire_date}
      areaOfInterest={analysis?.area_name}
      severityDistribution={severityDistributionForAPI}
      imageUrls={imageEntries}
      authorizedFetch={authorizedFetch}
      baseUrl={baseUrl}
    />
    </>
  );
}

export default AnalysisDetail;
