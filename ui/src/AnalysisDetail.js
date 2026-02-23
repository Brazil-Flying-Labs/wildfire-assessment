import { useCallback, useEffect, useRef, useState, useMemo } from "react";
import AIAnalysisModal from "./AIAnalysisModal";
import { useLanguage } from "./LanguageContext";

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
      if (!err?.isSessionExpired) console.error("Error loading analysis:", err);
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

  const formatDate = (dateString) => {
    if (!dateString) return "-";
    const date = new Date(dateString);
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, "0");
    const d = String(date.getDate()).padStart(2, "0");
    return `${y}/${m}/${d}`;
  };

  const formatDateTime = (dateString) => {
    if (!dateString) return "-";
    const date = new Date(dateString);
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, "0");
    const d = String(date.getDate()).padStart(2, "0");
    const hh = String(date.getHours()).padStart(2, "0");
    const mm = String(date.getMinutes()).padStart(2, "0");
    return `${y}/${m}/${d} ${hh}:${mm}`;
  };

  const formatNumber = (num) => {
    if (num === null || num === undefined) return "-";
    return Number(num).toLocaleString(undefined, {
      minimumFractionDigits: 0,
      maximumFractionDigits: 2,
    });
  };

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

  const severityColorMap = useMemo(
    () => ({
      "Unburned": "#28a745",
      "Low Severity": "#ffc107",
      "Moderate Severity": "#fd7e14",
      "High Severity": "#dc3545",
      "Very High Severity": "#6f42c1"
    }),
    []
  );

  const severityTranslationMap = useMemo(
    () => ({
      "Unburned": t("severity.unburned"),
      "Low Severity": t("severity.low"),
      "Moderate Severity": t("severity.moderate"),
      "High Severity": t("severity.high"),
      "Very High Severity": t("severity.veryHigh"),
      "Total Burned Area": t("severity.totalBurned"),
      "Total Area": t("severity.totalArea"),
    }),
    [t]
  );

  const severityEntries = useMemo(() => {
    const mapData = analysis?.severity_data;
    if (!mapData) return [];

    try {
      const parsed =
        typeof mapData === "string" ? JSON.parse(mapData) : mapData || {};
      const entries = Object.entries(parsed).map(([name, metrics]) => ({
        name,
        area: metrics?.area_ha ?? metrics?.area ?? null,
        percent: metrics?.ratio_percent ?? metrics?.percent ?? null,
      }));

      const severityOrder = [
        "Unburned",
        "Low Severity",
        "Moderate Severity",
        "High Severity",
        "Very High Severity",
        "Total Burned Area",
        "Total Area",
      ];

      entries.sort((a, b) => {
        const orderA = severityOrder.indexOf(a.name);
        const orderB = severityOrder.indexOf(b.name);
        if (orderA === -1 && orderB === -1) {
          return a.name.localeCompare(b.name);
        }
        if (orderA === -1) return 1;
        if (orderB === -1) return -1;
        return orderA - orderB;
      });

      return entries;
    } catch (error) {
      console.error("Failed to parse severity data:", error);
      return [];
    }
  }, [analysis]);

  const severityDistributionForAPI = useMemo(() => {
    const result = {};
    for (const { name, area, percent } of severityEntries) {
      result[name] = { area_ha: area, percent };
    }
    return result;
  }, [severityEntries]);

  const handleDownloadSeverityCsv = useCallback(() => {
    if (!severityEntries.length) return;
    const header = "Severity,Area (ha),Percent\n";
    const rows = severityEntries
      .map(({ name, area, percent }) => {
        const areaVal = area !== null && area !== undefined ? area : "";
        const pctVal = percent !== null && percent !== undefined ? percent : "";
        return `"${name}",${areaVal},${pctVal}`;
      })
      .join("\n");
    const blob = new Blob([header + rows], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "severity_distribution.csv";
    link.click();
    URL.revokeObjectURL(url);
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
      // Clear any existing interval for this deliverable
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

  // On analysis load, detect in-progress deliverables and resume polling
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

  // Cleanup polling intervals on unmount
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
        if (!err?.isSessionExpired) console.error("Failed to request scientific deliverable:", err);
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
        <button
          type="button"
          className="btn btn-outline-secondary btn-sm d-flex align-items-center gap-1"
          onClick={onBack}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="19" y1="12" x2="5" y2="12" />
            <polyline points="12 19 5 12 12 5" />
          </svg>
          {t("common.back")}
        </button>
      </div>
    );
  }

  return (
    <>
    <div className="analysis-detail p-4">
      {/* Header with back link */}
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
          <button
            type="button"
            className="btn btn-outline-secondary btn-sm d-flex align-items-center gap-1 no-print"
            onClick={onBack}
            title={t("common.back")}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="19" y1="12" x2="5" y2="12" />
              <polyline points="12 19 5 12 12 5" />
            </svg>
            {t("common.back")}
          </button>
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

      {/* Severity Distribution */}
      {severityEntries.length > 0 && (
        <div className="card shadow-sm mb-4">
          <div className="card-header d-flex align-items-center justify-content-between">
            <h3 className="h5 mb-0">{t("analysisDetail.severityDistribution")}</h3>
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
                    <th scope="col">{t("analysisDetail.severity")}</th>
                    <th scope="col">{t("analysisDetail.areaHa")}</th>
                    <th scope="col">{t("analysisDetail.percent")}</th>
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
                                width: '12px',
                                height: '12px',
                                backgroundColor: severityColorMap[name]
                              }}
                            />
                          )}
                          {severityTranslationMap[name] || name}
                        </span>
                      </td>
                      <td>{formatNumber(area)} ha</td>
                      <td>{formatNumber(percent)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Images */}
      <div className="card shadow-sm mb-4">
        <div className="card-header">
          <h3 className="h5 mb-0">{t("analysisDetail.images")}</h3>
        </div>
        <div className="card-body">
          {imageEntries.length > 0 ? (
            <div className="row g-3">
              {imageEntries.map(({ label, url }) => (
                <div className="col-md-6 col-lg-4" key={label}>
                  <div className="text-center">
                    <div className="fw-semibold mb-2">{label}</div>
                    <a href={url} target="_blank" rel="noopener noreferrer">
                      <img
                        src={url}
                        alt={label}
                        className="img-fluid rounded border"
                        style={{ height: "300px", objectFit: "contain" }}
                      />
                    </a>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-muted mb-0">{t("analysisDetail.noImages")}</p>
          )}
        </div>
      </div>

      {/* Scientific Deliverables */}
      <div className="card shadow-sm mb-4 no-print" ref={deliverablesRef}>
        <div className="card-header">
          <h3 className="h5 mb-0">{t("app.deliverableTitle")}</h3>
        </div>
        <div className="card-body">
          <p className="small text-muted mb-3">
            {t("app.deliverableHint")}
          </p>
          <div className="d-flex flex-wrap gap-3">
            {scientificDeliverables.map(({ label, value, urlKey }) => {
              const status = deliverableStatus[value] || {};
              const existingUrl = analysis?.[urlKey];
              const isProcessing = status.loading || status.polling;
              const cardClass = existingUrl
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
                    {existingUrl ? (
                      <a
                        href={existingUrl}
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
                          onClick={() => handleScientificDeliverable(value)}
                        >
                          {t("common.tryAgain")}
                        </button>
                      </div>
                    ) : (
                      <button
                        type="button"
                        className="btn btn-sm btn-outline-primary"
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
