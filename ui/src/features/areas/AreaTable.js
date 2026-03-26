import DeleteConfirmation from "../../components/DeleteConfirmation";
import KebabMenu from "../../components/KebabMenu";

const editIcon = (
  <svg
    width="16"
    height="16"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
  >
    <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
    <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
  </svg>
);

const downloadIcon = (
  <svg
    width="16"
    height="16"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
  >
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
    <polyline points="7 10 12 15 17 10" />
    <line x1="12" y1="15" x2="12" y2="3" />
  </svg>
);

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

function AreaTable({
  areas,
  deleteConfirm,
  setDeleteConfirm,
  deleting,
  handleDelete,
  openMenuId,
  toggleMenu,
  closeMenu,
  openEditModal,
  onDownloadGeojson,
  t,
}) {
  if (areas.length === 0) {
    return (
      <div className="p-4 text-center text-muted">{t("areas.noAreas")}</div>
    );
  }

  const menuItems = (area) => [
    {
      label: t("areas.edit"),
      icon: editIcon,
      onClick: () => {
        closeMenu();
        openEditModal(area);
      },
    },
    {
      label: t("areas.downloadGeojson"),
      icon: downloadIcon,
      onClick: () => {
        closeMenu();
        onDownloadGeojson(area);
      },
    },
    {
      label: t("areas.delete"),
      icon: deleteIcon,
      className: "text-danger",
      onClick: () => {
        closeMenu();
        setDeleteConfirm(area.id);
      },
    },
  ];

  const countryLabel = (area) =>
    area.country_name ? `${area.country_name} (${area.country_code})` : "-";

  const renderActions = (area, desktopClass = "") => (
    <>
      {deleteConfirm === area.id ? (
        <DeleteConfirmation
          onConfirm={() => handleDelete(area.id)}
          onCancel={() => setDeleteConfirm(null)}
          confirming={deleting}
          confirmLabel={t("areas.confirmDelete")}
          cancelLabel={t("areas.cancel")}
          className={desktopClass}
        />
      ) : (
        <KebabMenu
          items={menuItems(area)}
          isOpen={openMenuId === area.id}
          onToggle={() => toggleMenu(area.id)}
          onClose={closeMenu}
          ariaLabel={t("areas.actions")}
        />
      )}
    </>
  );

  return (
    <>
      {/* Desktop table */}
      <div className="table-responsive d-none d-md-block">
        <table className="table table-hover mb-0 areas-table">
          <thead className="table-light">
            <tr>
              <th scope="col">{t("areas.name")}</th>
              <th scope="col">{t("areas.country")}</th>
              <th
                scope="col"
                className="text-end"
                style={{ width: "50px" }}
              >
                <span className="visually-hidden">{t("areas.actions")}</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {areas.map((area) => (
              <tr key={area.id}>
                <td>
                  <strong>{area.name}</strong>
                </td>
                <td>{countryLabel(area)}</td>
                <td className="text-end">
                  {renderActions(area, "justify-content-end")}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Mobile cards */}
      <div className="d-md-none mobile-card-list">
        {areas.map((area) => (
          <div key={area.id} className="mobile-card">
            <div className="mobile-card-header">
              <div className="mobile-card-header-text">
                <span className="mobile-card-title">{area.name}</span>
                <span className="text-muted small">{countryLabel(area)}</span>
              </div>
              <div className="mobile-card-actions">
                {renderActions(area)}
              </div>
            </div>
          </div>
        ))}
      </div>
    </>
  );
}

export default AreaTable;
