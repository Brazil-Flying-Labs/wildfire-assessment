import { formatNumber } from "../../utils/formatting";

function SeverityTable({
  severityEntries,
  severityColorMap,
  severityTranslationMap,
  onDownloadCsv,
  t,
}) {
  if (severityEntries.length === 0) return null;

  return (
    <div className="card shadow-sm mb-4">
      <div className="card-header d-flex align-items-center justify-content-between">
        <h3 className="h5 mb-0">{t("analysisDetail.severityDistribution")}</h3>
        <button
          type="button"
          className="btn btn-outline-secondary btn-sm d-flex align-items-center gap-1"
          onClick={onDownloadCsv}
          title={t("common.downloadCsv")}
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
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
                            width: "12px",
                            height: "12px",
                            backgroundColor: severityColorMap[name],
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
  );
}

export default SeverityTable;
