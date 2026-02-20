import { useCallback, useEffect, useState, useMemo } from "react";
import { useLanguage } from "./LanguageContext";

function AnalysisDetail({ authorizedFetch, baseUrl, analysisId, onBack }) {
  const { t } = useLanguage();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [analysis, setAnalysis] = useState(null);

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
          className="btn btn-secondary"
          onClick={onBack}
        >
          {t("analysisDetail.backToDashboard")}
        </button>
      </div>
    );
  }

  return (
    <div className="analysis-detail p-4">
      {/* Header with back button */}
      <div className="d-flex align-items-center gap-3 mb-4">
        <button
          type="button"
          className="btn btn-outline-secondary"
          onClick={onBack}
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="19" y1="12" x2="5" y2="12" />
            <polyline points="12 19 5 12 12 5" />
          </svg>
        </button>
        <h2 className="h4 mb-0">{t("analysisDetail.title")}</h2>
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
          <div className="card-header">
            <h3 className="h5 mb-0">{t("analysisDetail.severityDistribution")}</h3>
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
                              className="d-inline-block rounded"
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

      {/* Raw Data */}
      <div className="card shadow-sm">
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
