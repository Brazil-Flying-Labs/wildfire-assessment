function AddWidgetModal({ hiddenWidgets, onAdd, onClose, t }) {
  return (
    <>
      <div className="modal-backdrop fade show" onClick={onClose}></div>
      <div className="modal fade show d-block" tabIndex="-1" role="dialog">
        <div className="modal-dialog modal-dialog-centered" role="document">
          <div className="modal-content">
            <div className="modal-header">
              <h5 className="modal-title">{t("dashboard.addWidget")}</h5>
              <button
                type="button"
                className="btn-close"
                onClick={onClose}
                aria-label={t("common.close")}
              ></button>
            </div>
            <div className="modal-body">
              <p className="text-muted small mb-3">
                {t("dashboard.addWidgetDesc")}
              </p>
              {hiddenWidgets.length === 0 ? (
                <p className="text-center text-muted">{t("dashboard.noData")}</p>
              ) : (
                <div className="list-group">
                  {hiddenWidgets.map((w) => (
                    <div
                      key={w.id}
                      className="list-group-item d-flex justify-content-between align-items-center"
                    >
                      <span>{t(w.titleKey)}</span>
                      <button
                        type="button"
                        className="btn btn-sm btn-primary"
                        onClick={() => onAdd(w.id)}
                      >
                        {t("dashboard.add")}
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

export default AddWidgetModal;
