import { useCallback, useEffect, useState, useMemo } from "react";
import { useLanguage } from "./LanguageContext";

function AnalysisDetail({ authorizedFetch, baseUrl, analysisId, onBack }) {
  const { t } = useLanguage();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [deliverableStatus, setDeliverableStatus] = useState({});
  const [deliverableAlert, setDeliverableAlert] = useState(null);

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

  const formatDate = (dateString) => {
    if (!dateString) return "-";
    const date = new Date(dateString);
    return date.toLocaleDateString();
  };

  const formatDateTime = (dateString) => {
    if (!dateString) return "-";
    const date = new Date(dateString);
    return date.toLocaleString();
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
      { label: t("analysisDetail.preFireRgb"), url: analysis.rgb_pre_fire_url },
      { label: t("analysisDetail.postFireRgb"), url: analysis.rgb_post_fire_url },
      { label: t("analysisDetail.dndvi"), url: analysis.dndvi_url },
      { label: t("analysisDetail.dnbr"), url: analysis.dnbr_url },
      { label: t("analysisDetail.rbr"), url: analysis.rbr_url },
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
      { label: "RGB Pre-fire", value: "RGB_PRE_FIRE" },
      { label: "RGB Post-fire", value: "RGB_POST_FIRE" },
      { label: "dNBR", value: "DNBR" },
      { label: "RBR", value: "RBR" },
      { label: "dNDVI", value: "DNDVI" },
    ],
    []
  );

  const handleScientificDeliverable = useCallback(
    async (deliverableName) => {
      if (!analysis) return;

      setDeliverableAlert(null);
      setDeliverableStatus((prev) => ({
        ...prev,
        [deliverableName]: { loading: true, error: null, taskId: null },
      }));

      try {
        const queryParams = new URLSearchParams({
          pre_fire_date: analysis.pre_fire_date,
          post_fire_date: analysis.post_fire_date,
          deliverable: deliverableName,
        });

        const url = `${baseUrl}/area_of_interest/${analysis.area_of_interest}/scientific_deliverable/?${queryParams.toString()}`;
        const response = await authorizedFetch(url, { method: "POST" });

        if (!response.ok) {
          throw new Error(t("app.errorDeliverable", { status: response.status }));
        }

        const data = await response.json();
        const label = scientificDeliverables.find((d) => d.value === deliverableName)?.label || deliverableName;
        setDeliverableStatus((prev) => ({
          ...prev,
          [deliverableName]: { loading: false, taskId: data.task_id || null },
        }));
        setDeliverableAlert({
          type: "success",
          message: t("app.deliverableSuccess", { label }),
        });
      } catch (err) {
        console.error("Failed to request scientific deliverable:", err);
        setDeliverableStatus((prev) => ({
          ...prev,
          [deliverableName]: { loading: false, error: err.message, taskId: null },
        }));
      }
    },
    [analysis, authorizedFetch, baseUrl, scientificDeliverables, t]
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
          className="btn btn-link text-decoration-none p-0"
          onClick={onBack}
        >
          ← {t("analysisDetail.backToDashboard")}
        </button>
      </div>
    );
  }

  return (
    <div className="analysis-detail p-4">
      {/* Header with back link */}
      <div className="d-flex align-items-center justify-content-between mb-4">
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
            className="btn btn-link text-decoration-none p-0 no-print"
            onClick={onBack}
          >
            ← {t("analysisDetail.backToDashboard")}
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
                          {name}
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
                        style={{ maxHeight: "300px" }}
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
      <div className="card shadow-sm mb-4 no-print">
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
              return (
                <div
                  key={value}
                  className="d-flex flex-column align-items-start"
                >
                  <button
                    type="button"
                    className="btn btn-link p-0"
                    disabled={status.loading}
                    onClick={() => handleScientificDeliverable(value)}
                    title={t("app.deliverableTooltip", { label })}
                  >
                    {status.loading
                      ? t("app.deliverableRequesting", { label })
                      : label}
                  </button>
                  {status.taskId ? (
                    <span className="small text-success">
                      {t("app.taskId", { taskId: status.taskId })}
                    </span>
                  ) : null}
                  {!status.loading && status.error ? (
                    <span className="small text-danger">
                      {status.error}
                    </span>
                  ) : null}
                </div>
              );
            })}
          </div>
          {deliverableAlert ? (
            <div
              className={`alert alert-${deliverableAlert.type} mt-3`}
              role="alert"
            >
              {deliverableAlert.message}
            </div>
          ) : null}
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
  );
}

export default AnalysisDetail;
