import { useMemo } from "react";
import ReactMarkdown from "react-markdown";
import { formatDate, formatDateTime, formatNumber } from "../../utils/formatting";
import { SEVERITY_COLORS, getSeverityTranslations } from "../../constants/severity";
import "./PrintReport.css";

const MOSAIC_STRATEGY_LABELS = {
  best_date_mosaic: "app.mosaicBestDate",
  best_date_masked_mosaic: "app.mosaicBestDateMasked",
  best_available_per_tile_mosaic: "app.mosaicBestAvailable",
  cloud_masked_light_mosaic: "app.mosaicCloudMasked",
};

function PrintReport({ analysis, severityEntries, imageEntries, reportSummary, reportLoading, onRegenerate, t }) {
  const severityTranslationMap = useMemo(() => getSeverityTranslations(t), [t]);
  const logoSrc = useMemo(() => `${process.env.PUBLIC_URL}/logo-report.jpeg`, []);
  const generatedAt = useMemo(() => formatDateTime(new Date().toISOString()), []);

  if (!analysis) return null;

  const maxPercent = Math.max(
    ...severityEntries.filter((e) => e.percent != null).map((e) => e.percent),
    1
  );

  return (
    <div className="print-report">
      {/* ── Header ── */}
      <div className="pr-header">
        <div className="pr-header-left">
          <img src={logoSrc} alt="" className="pr-logo" />
          <div>
            <h1 className="pr-title">{t("report.title")}</h1>
            <p className="pr-subtitle">{t("report.subtitle")}</p>
          </div>
        </div>
        <div className="pr-header-right">
          <div className="pr-meta-row">
            <span className="pr-meta-label">{t("report.generatedOn")}</span>
            <span>{generatedAt}</span>
          </div>
          <div className="pr-meta-row">
            <span className="pr-meta-label">{t("report.analysisId")}</span>
            <span>#{analysis.id}</span>
          </div>
        </div>
      </div>

      <div className="pr-divider" />

      {/* ── Area Banner ── */}
      <div className="pr-area-banner">
        <h2 className="pr-area-name">{analysis.area_name}</h2>
        <div className="pr-area-meta">
          <span>{analysis.country_name}</span>
          <span className="pr-sep">|</span>
          <span>
            {formatDate(analysis.pre_fire_date)} &mdash;{" "}
            {formatDate(analysis.post_fire_date)}
          </span>
        </div>
      </div>

      {/* ── Key Metrics ── */}
      <div className="pr-metrics">
        <div className="pr-metric-card">
          <div className="pr-metric-value pr-danger">
            {formatNumber(analysis.total_burned_ha)}
          </div>
          <div className="pr-metric-unit">ha</div>
          <div className="pr-metric-label">{t("report.totalBurned")}</div>
        </div>
      </div>

      {/* ── Executive Summary (AI-generated) ── */}
      <div className="pr-section">
        <div className="pr-section-head">
          <svg className="pr-section-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
            <line x1="16" y1="13" x2="8" y2="13" />
            <line x1="16" y1="17" x2="8" y2="17" />
            <polyline points="10 9 9 9 8 9" />
          </svg>
          <h3>{t("report.executiveSummary")}</h3>
          <span className="pr-ai-badge">{t("report.aiGenerated")}</span>
          {onRegenerate && (
            <button
              type="button"
              className="btn btn-outline-primary btn-sm ms-auto no-print"
              onClick={onRegenerate}
              disabled={reportLoading}
            >
              {reportLoading ? t("report.regenerating") : t("report.regenerate")}
            </button>
          )}
        </div>
        <div className="pr-summary-body pr-markdown">
          {reportSummary ? (
            <ReactMarkdown>{reportSummary}</ReactMarkdown>
          ) : (
            <p className="text-muted fst-italic">{t("report.noSummary")}</p>
          )}
        </div>
      </div>

      {/* ── Severity Distribution ── */}
      {severityEntries.length > 0 && (
        <div className="pr-section">
          <div className="pr-section-head">
            <svg className="pr-section-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="3" width="18" height="18" rx="2" />
              <path d="M3 9h18M9 21V9" />
            </svg>
            <h3>{t("analysisDetail.severityDistribution")}</h3>
          </div>
          <table className="pr-table">
            <thead>
              <tr>
                <th>{t("analysisDetail.severity")}</th>
                <th style={{ width: "35%" }}>{t("report.distribution")}</th>
                <th>{t("analysisDetail.areaHa")}</th>
                <th>{t("analysisDetail.percent")}</th>
              </tr>
            </thead>
            <tbody>
              {severityEntries.map(({ name, area, percent }) => (
                <tr key={name}>
                  <td>
                    <span className="pr-sev-cell">
                      {SEVERITY_COLORS[name] && (
                        <span
                          className="pr-sev-dot severity-color"
                          style={{ backgroundColor: SEVERITY_COLORS[name] }}
                        />
                      )}
                      {severityTranslationMap[name] || name}
                    </span>
                  </td>
                  <td>
                    {percent != null && (
                      <div className="pr-bar-track">
                        <div
                          className="pr-bar severity-color"
                          style={{
                            width: `${Math.max((percent / maxPercent) * 100, 1)}%`,
                            backgroundColor: SEVERITY_COLORS[name] || "#6c757d",
                          }}
                        />
                      </div>
                    )}
                  </td>
                  <td className="pr-num">{formatNumber(area)} ha</td>
                  <td className="pr-num">{formatNumber(percent)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* ── Satellite Imagery ── */}
      {imageEntries.length > 0 && (
        <div className="pr-section pr-images-section">
          <div className="pr-section-head">
            <svg className="pr-section-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="3" width="18" height="18" rx="2" />
              <circle cx="8.5" cy="8.5" r="1.5" />
              <path d="m21 15-5-5L5 21" />
            </svg>
            <h3>{t("report.satelliteImagery")}</h3>
          </div>
          <div className="pr-images">
            {imageEntries.map(({ label, url }) => (
              <div className="pr-img-block" key={label}>
                <img src={url} alt={label} className="pr-img" />
                <div className="pr-img-caption">{label}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Analysis Parameters ── */}
      <div className="pr-section">
        <div className="pr-section-head">
          <svg className="pr-section-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="3" />
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
          </svg>
          <h3>{t("report.analysisParameters")}</h3>
        </div>
        <div className="pr-params">
          <div className="pr-param">
            <span className="pr-param-label">{t("analysisDetail.runDate")}</span>
            <span>{formatDateTime(analysis.created_at)}</span>
          </div>
          <div className="pr-param">
            <span className="pr-param-label">{t("app.cloudThreshold")}</span>
            <span>
              {analysis.cloud_threshold != null
                ? `${analysis.cloud_threshold}%`
                : "-"}
            </span>
          </div>
          <div className="pr-param">
            <span className="pr-param-label">{t("app.mosaicStrategy")}</span>
            <span>
              {analysis.pre_fire_mosaic_strategy
                ? t(
                    MOSAIC_STRATEGY_LABELS[analysis.pre_fire_mosaic_strategy] ||
                      analysis.pre_fire_mosaic_strategy
                  )
                : "-"}
            </span>
          </div>
          <div className="pr-param">
            <span className="pr-param-label">{t("analysisDetail.status")}</span>
            <span className="pr-status">{analysis.status}</span>
          </div>
          <div className="pr-param">
            <span className="pr-param-label">{t("app.daysBeforeAfter")}</span>
            <span>
              {analysis.days_before_after != null
                ? `${analysis.days_before_after} ${t("app.daysBeforeAfterSuffix")}`
                : "-"}
            </span>
          </div>
        </div>
      </div>

      {/* ── Image Sources (Provenance) ── */}
      {analysis.provenance && analysis.provenance.length > 0 && (
        <>
          {analysis.provenance.some((p) => p.phase === "pre_fire") && (
            <div className="pr-section">
              <div className="pr-section-head">
                <svg className="pr-section-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z" />
                  <line x1="4" y1="22" x2="4" y2="15" />
                </svg>
                <h3>{t("report.preFireSources")}</h3>
              </div>
              <table className="pr-table">
                <thead>
                  <tr>
                    <th>{t("report.provenanceDate")}</th>
                    <th>{t("report.provenanceSceneId")}</th>
                    <th>{t("report.provenanceSpacecraft")}</th>
                    <th className="pr-num">{t("report.provenanceCloud")}</th>
                  </tr>
                </thead>
                <tbody>
                  {analysis.provenance
                    .filter((p) => p.phase === "pre_fire")
                    .map((p) => (
                      <tr key={p.id}>
                        <td>{formatDate(p.date)}</td>
                        <td className="pr-scene-id">{p.scene_id}</td>
                        <td>{p.spacecraft_name || "-"}</td>
                        <td className="pr-num">
                          {p.cloud_percent != null
                            ? `${formatNumber(p.cloud_percent)}%`
                            : "-"}
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          )}
          {analysis.provenance.some((p) => p.phase === "post_fire") && (
            <div className="pr-section">
              <div className="pr-section-head">
                <svg className="pr-section-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z" />
                  <line x1="4" y1="22" x2="4" y2="15" />
                </svg>
                <h3>{t("report.postFireSources")}</h3>
              </div>
              <table className="pr-table">
                <thead>
                  <tr>
                    <th>{t("report.provenanceDate")}</th>
                    <th>{t("report.provenanceSceneId")}</th>
                    <th>{t("report.provenanceSpacecraft")}</th>
                    <th className="pr-num">{t("report.provenanceCloud")}</th>
                  </tr>
                </thead>
                <tbody>
                  {analysis.provenance
                    .filter((p) => p.phase === "post_fire")
                    .map((p) => (
                      <tr key={p.id}>
                        <td>{formatDate(p.date)}</td>
                        <td className="pr-scene-id">{p.scene_id}</td>
                        <td>{p.spacecraft_name || "-"}</td>
                        <td className="pr-num">
                          {p.cloud_percent != null
                            ? `${formatNumber(p.cloud_percent)}%`
                            : "-"}
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      {/* ── Footer ── */}
      <div className="pr-footer">
        <div className="pr-disclaimer" style={{ color: "#000" }}>{t("report.disclaimer")}</div>
        <div className="pr-footer-brand" style={{ color: "#333" }}>
          <span>{t("report.generatedBy")}</span>
          <span className="pr-sep">|</span>
          <span>{generatedAt}</span>
        </div>
      </div>
    </div>
  );
}

export default PrintReport;
