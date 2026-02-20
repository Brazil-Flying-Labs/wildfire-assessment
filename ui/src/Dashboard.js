import { useCallback, useEffect, useState } from "react";
import { useLanguage } from "./LanguageContext";

function InfoTooltip({ text }) {
  return (
    <span className="info-tooltip">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="12" cy="12" r="10" />
        <line x1="12" y1="16" x2="12" y2="12" />
        <line x1="12" y1="8" x2="12.01" y2="8" />
      </svg>
      <span className="info-tooltip-text">{text}</span>
    </span>
  );
}

function Dashboard({ authorizedFetch, baseUrl, onAnalysisClick }) {
  const { t } = useLanguage();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [stats, setStats] = useState(null);

  const loadDashboard = useCallback(async () => {
    if (!baseUrl) return;

    setLoading(true);
    setError(null);

    try {
      const response = await authorizedFetch(`${baseUrl}/dashboard/`);
      if (response.ok) {
        const data = await response.json();
        setStats(data);
      } else {
        throw new Error(t("dashboard.errorLoading"));
      }
    } catch (err) {
      console.error("Error loading dashboard:", err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [authorizedFetch, baseUrl, t]);

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  const formatDate = (dateString) => {
    if (!dateString) return "-";
    const date = new Date(dateString);
    return date.toLocaleDateString();
  };

  const formatNumber = (num) => {
    if (num === null || num === undefined) return "-";
    return Number(num).toLocaleString(undefined, {
      minimumFractionDigits: 0,
      maximumFractionDigits: 2,
    });
  };

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
            onClick={loadDashboard}
          >
            {t("common.tryAgain")}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="dashboard p-4">
      <h2 className="h4 mb-4">{t("dashboard.title")}</h2>

      {/* Stats Cards */}
      <div className="row g-3 mb-4">
        {/* 1. Areas Monitored */}
        <div className="col-6 col-md">
          <div className="card h-100 shadow-sm stat-card">
            <div className="card-body text-center">
              <div className="stat-icon mb-2">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6" />
                  <line x1="8" y1="2" x2="8" y2="18" />
                  <line x1="16" y1="6" x2="16" y2="22" />
                </svg>
              </div>
              <h3 className="stat-value h2 mb-1">{formatNumber(stats?.total_areas)}</h3>
              <p className="stat-label text-muted mb-0 small">
                {t("dashboard.totalAreas")}
                <InfoTooltip text={t("dashboard.tooltipTotalAreas")} />
              </p>
            </div>
          </div>
        </div>

        {/* 2. Total Analyses */}
        <div className="col-6 col-md">
          <div className="card h-100 shadow-sm stat-card">
            <div className="card-body text-center">
              <div className="stat-icon mb-2">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
                </svg>
              </div>
              <h3 className="stat-value h2 mb-1">{formatNumber(stats?.total_analyses)}</h3>
              <p className="stat-label text-muted mb-0 small">
                {t("dashboard.totalAnalyses")}
                <InfoTooltip text={t("dashboard.tooltipTotalAnalyses")} />
              </p>
            </div>
          </div>
        </div>

        {/* 3. Total Area Analyzed */}
        <div className="col-6 col-md">
          <div className="card h-100 shadow-sm stat-card">
            <div className="card-body text-center">
              <div className="stat-icon mb-2 text-primary">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="10" />
                  <polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76" />
                </svg>
              </div>
              <h3 className="stat-value h2 mb-1">{formatNumber(stats?.total_analyzed_ha)}</h3>
              <p className="stat-label text-muted mb-0 small">
                {t("dashboard.totalAnalyzedHa")}
                <InfoTooltip text={t("dashboard.tooltipAnalyzedHa")} />
              </p>
            </div>
          </div>
        </div>

        {/* 4. Total Area Burned */}
        <div className="col-6 col-md">
          <div className="card h-100 shadow-sm stat-card">
            <div className="card-body text-center">
              <div className="stat-icon mb-2 text-danger">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z" />
                </svg>
              </div>
              <h3 className="stat-value h2 mb-1">{formatNumber(stats?.total_burned_ha)}</h3>
              <p className="stat-label text-muted mb-0 small">
                {t("dashboard.totalBurnedHa")}
                <InfoTooltip text={t("dashboard.tooltipBurnedHa")} />
              </p>
            </div>
          </div>
        </div>

        {/* 5. Analyses This Month */}
        <div className="col-6 col-md">
          <div className="card h-100 shadow-sm stat-card">
            <div className="card-body text-center">
              <div className="stat-icon mb-2 text-success">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
                  <line x1="16" y1="2" x2="16" y2="6" />
                  <line x1="8" y1="2" x2="8" y2="6" />
                  <line x1="3" y1="10" x2="21" y2="10" />
                </svg>
              </div>
              <h3 className="stat-value h2 mb-1">{formatNumber(stats?.analyses_this_month)}</h3>
              <p className="stat-label text-muted mb-0 small">
                {t("dashboard.analysesThisMonth")}
                <InfoTooltip text={t("dashboard.tooltipThisMonth")} />
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Insight Cards Row */}
      <div className="row g-3 mb-4">
        {/* Average Burn Severity */}
        <div className="col-md-4">
          <div className="card h-100 shadow-sm stat-card">
            <div className="card-body text-center">
              <div className="stat-icon mb-2 text-warning">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M14 14.76V3.5a2.5 2.5 0 0 0-5 0v11.26a4.5 4.5 0 1 0 5 0z" />
                </svg>
              </div>
              <h3 className="stat-value h2 mb-1">
                {stats?.average_burn_severity != null
                  ? formatNumber(stats.average_burn_severity)
                  : "-"}
              </h3>
              <p className="stat-label text-muted mb-0 small">
                {t("dashboard.avgBurnSeverity")}
                <InfoTooltip text={t("dashboard.tooltipAvgSeverity")} />
              </p>
            </div>
          </div>
        </div>

        {/* Most Analyzed Area */}
        <div className="col-md-4">
          <div className="card h-100 shadow-sm stat-card">
            <div className="card-body text-center">
              <div className="stat-icon mb-2 text-info">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
                  <circle cx="12" cy="10" r="3" />
                </svg>
              </div>
              <h3 className="stat-value h4 mb-1">
                {stats?.most_analyzed_area?.area_name || "-"}
              </h3>
              <p className="stat-label text-muted mb-0 small">
                {stats?.most_analyzed_area
                  ? `${stats.most_analyzed_area.run_count} ${t("dashboard.runs")}`
                  : t("dashboard.mostAnalyzedArea")}
                <InfoTooltip text={t("dashboard.tooltipMostAnalyzed")} />
              </p>
            </div>
          </div>
        </div>

        {/* Largest Fire */}
        <div className="col-md-4">
          <div className="card h-100 shadow-sm stat-card">
            <div className="card-body text-center">
              <div className="stat-icon mb-2 text-danger">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z" />
                </svg>
              </div>
              <h3 className="stat-value h4 mb-1">
                {stats?.largest_fire?.area_name || "-"}
              </h3>
              <p className="stat-label text-muted mb-0 small">
                {stats?.largest_fire
                  ? `${formatNumber(stats.largest_fire.burned_ha)} ha`
                  : t("dashboard.largestFire")}
                <InfoTooltip text={t("dashboard.tooltipLargestFire")} />
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Analyses */}
      <div className="card shadow-sm">
        <div className="card-header">
          <h3 className="h5 mb-0">{t("dashboard.recentAnalyses")}</h3>
        </div>
        <div className="card-body p-0">
          {!stats?.recent_analyses?.length ? (
            <div className="p-4 text-center text-muted">
              {t("dashboard.noAnalyses")}
            </div>
          ) : (
            <div className="table-responsive">
              <table className="table table-hover mb-0">
                <thead className="table-light">
                  <tr>
                    <th scope="col">{t("dashboard.area")}</th>
                    <th scope="col" className="d-none d-md-table-cell">{t("dashboard.country")}</th>
                    <th scope="col">{t("dashboard.dates")}</th>
                    <th scope="col" className="d-none d-md-table-cell">{t("dashboard.areaHa")}</th>
                    <th scope="col" className="d-none d-md-table-cell">{t("dashboard.burnedHa")}</th>
                    <th scope="col" className="d-none d-lg-table-cell">{t("dashboard.runDate")}</th>
                  </tr>
                </thead>
                <tbody>
                  {stats.recent_analyses.map((analysis) => (
                    <tr
                      key={analysis.id}
                      onClick={() => onAnalysisClick?.(analysis.id)}
                      style={{ cursor: onAnalysisClick ? "pointer" : "default" }}
                      role={onAnalysisClick ? "button" : undefined}
                      tabIndex={onAnalysisClick ? 0 : undefined}
                      onKeyDown={(e) => {
                        if (onAnalysisClick && (e.key === "Enter" || e.key === " ")) {
                          e.preventDefault();
                          onAnalysisClick(analysis.id);
                        }
                      }}
                    >
                      <td>
                        {analysis.area_name}
                        <div className="d-md-none text-muted small">
                          {analysis.country_name}
                        </div>
                      </td>
                      <td className="d-none d-md-table-cell">{analysis.country_name || "-"}</td>
                      <td>
                        <small>
                          {formatDate(analysis.pre_fire_date)} → {formatDate(analysis.post_fire_date)}
                        </small>
                      </td>
                      <td className="d-none d-md-table-cell">
                        {formatNumber(analysis.severity_data?.["Total Area"]?.area_ha)} ha
                      </td>
                      <td className="d-none d-md-table-cell">
                        {formatNumber(analysis.total_burned_ha)} ha
                      </td>
                      <td className="d-none d-lg-table-cell">
                        {formatDate(analysis.created_at)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default Dashboard;
