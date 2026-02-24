import KebabMenu from "../../components/KebabMenu";
import DeleteConfirmation from "../../components/DeleteConfirmation";
import { formatDate, formatNumber } from "../../utils/formatting";

function RecentAnalysesWidget({
  analyses,
  t,
  onAnalysisClick,
  deleteConfirmId,
  setDeleteConfirmId,
  deletingAnalysis,
  handleDeleteAnalysis,
  openMenuId,
  toggleMenu,
  closeMenu,
}) {
  const deleteIcon = (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
    >
      <polyline points="3 6 5 6 21 6" />
      <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
    </svg>
  );

  const rowProps = (analysisId) =>
    onAnalysisClick
      ? {
          onClick: () => onAnalysisClick(analysisId),
          style: { cursor: "pointer" },
          role: "button",
          tabIndex: 0,
          onKeyDown: (e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              onAnalysisClick(analysisId);
            }
          },
        }
      : { style: { cursor: "default" } };

  return (
    <div className="card shadow-sm">
      <div className="card-header">
        <h3 className="h5 mb-0">{t("dashboard.recentAnalyses")}</h3>
      </div>
      <div className="card-body p-0">
        {!analyses?.length ? (
          <div className="p-4 text-center text-muted">
            {t("dashboard.noAnalyses")}
          </div>
        ) : (
          <>
            {/* Desktop table */}
            <div className="table-responsive d-none d-md-block">
              <table className="table table-hover mb-0">
                <thead className="table-light">
                  <tr>
                    <th scope="col">{t("dashboard.area")}</th>
                    <th scope="col">{t("dashboard.country")}</th>
                    <th scope="col">{t("dashboard.dates")}</th>
                    <th scope="col">{t("dashboard.areaHa")}</th>
                    <th scope="col">{t("dashboard.burnedHa")}</th>
                    <th scope="col" className="d-none d-lg-table-cell">
                      {t("dashboard.runDate")}
                    </th>
                    <th scope="col" style={{ width: "1%" }}></th>
                  </tr>
                </thead>
                <tbody>
                  {analyses.map((analysis) => (
                    <tr key={analysis.id} {...rowProps(analysis.id)}>
                      <td>{analysis.area_name}</td>
                      <td>{analysis.country_name || "-"}</td>
                      <td>
                        <small>
                          {formatDate(analysis.pre_fire_date)} →{" "}
                          {formatDate(analysis.post_fire_date)}
                        </small>
                      </td>
                      <td>
                        {formatNumber(
                          analysis.severity_data?.["Total Area"]?.area_ha
                        )}{" "}
                        ha
                      </td>
                      <td>{formatNumber(analysis.total_burned_ha)} ha</td>
                      <td className="d-none d-lg-table-cell">
                        {formatDate(analysis.created_at)}
                      </td>
                      <td
                        onClick={(e) => e.stopPropagation()}
                        className="text-end"
                      >
                        {deleteConfirmId === analysis.id ? (
                          <DeleteConfirmation
                            onConfirm={() => handleDeleteAnalysis(analysis.id)}
                            onCancel={() => setDeleteConfirmId(null)}
                            confirming={deletingAnalysis}
                            confirmLabel={t("areas.confirmDelete")}
                            cancelLabel={t("areas.cancel")}
                            className="justify-content-end"
                          />
                        ) : (
                          <KebabMenu
                            items={[
                              {
                                label: t("dashboard.deleteAnalysis"),
                                icon: deleteIcon,
                                className: "text-danger",
                                onClick: () => {
                                  closeMenu();
                                  setDeleteConfirmId(analysis.id);
                                },
                              },
                            ]}
                            isOpen={openMenuId === analysis.id}
                            onToggle={() => toggleMenu(analysis.id)}
                            onClose={closeMenu}
                            ariaLabel={t("dashboard.actions")}
                          />
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Mobile cards */}
            <div className="d-md-none mobile-card-list">
              {analyses.map((analysis) => (
                <div
                  key={analysis.id}
                  className="mobile-card"
                  {...rowProps(analysis.id)}
                >
                  <div className="mobile-card-header">
                    <div className="mobile-card-header-text">
                      <span className="mobile-card-title">
                        {analysis.area_name}
                      </span>
                      <span className="mobile-card-badge">
                        {analysis.country_name || "-"}
                      </span>
                    </div>
                    <div
                      className="mobile-card-actions"
                      onClick={(e) => e.stopPropagation()}
                    >
                      {deleteConfirmId === analysis.id ? (
                        <DeleteConfirmation
                          onConfirm={() => handleDeleteAnalysis(analysis.id)}
                          onCancel={() => setDeleteConfirmId(null)}
                          confirming={deletingAnalysis}
                          confirmLabel={t("areas.confirmDelete")}
                          cancelLabel={t("areas.cancel")}
                        />
                      ) : (
                        <KebabMenu
                          items={[
                            {
                              label: t("dashboard.deleteAnalysis"),
                              icon: deleteIcon,
                              className: "text-danger",
                              onClick: () => {
                                closeMenu();
                                setDeleteConfirmId(analysis.id);
                              },
                            },
                          ]}
                          isOpen={openMenuId === analysis.id}
                          onToggle={() => toggleMenu(analysis.id)}
                          onClose={closeMenu}
                          ariaLabel={t("dashboard.actions")}
                        />
                      )}
                    </div>
                  </div>
                  <div className="mobile-card-body">
                    <div className="mobile-card-row">
                      <span className="mobile-card-label">
                        {t("dashboard.dates")}
                      </span>
                      <span>
                        {formatDate(analysis.pre_fire_date)} →{" "}
                        {formatDate(analysis.post_fire_date)}
                      </span>
                    </div>
                    <div className="mobile-card-row">
                      <span className="mobile-card-label">
                        {t("dashboard.areaHa")}
                      </span>
                      <span>
                        {formatNumber(
                          analysis.severity_data?.["Total Area"]?.area_ha
                        )}{" "}
                        ha
                      </span>
                    </div>
                    <div className="mobile-card-row">
                      <span className="mobile-card-label">
                        {t("dashboard.burnedHa")}
                      </span>
                      <span>{formatNumber(analysis.total_burned_ha)} ha</span>
                    </div>
                    <div className="mobile-card-row">
                      <span className="mobile-card-label">
                        {t("dashboard.runDate")}
                      </span>
                      <span>{formatDate(analysis.created_at)}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default RecentAnalysesWidget;
