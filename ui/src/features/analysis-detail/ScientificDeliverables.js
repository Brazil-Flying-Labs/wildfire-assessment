import { forwardRef } from "react";

const ScientificDeliverables = forwardRef(function ScientificDeliverables(
  { analysis, scientificDeliverables, deliverableStatus, onRequest, t },
  ref
) {
  return (
    <div className="card shadow-sm mb-4 no-print" ref={ref}>
      <div className="card-header">
        <h3 className="h5 mb-0">{t("app.deliverableTitle")}</h3>
      </div>
      <div className="card-body">
        <p className="small text-muted mb-3">{t("app.deliverableHint")}</p>
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
                      <svg
                        width="14"
                        height="14"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      >
                        <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
                        <polyline points="15 3 21 3 21 9" />
                        <line x1="10" y1="14" x2="21" y2="3" />
                      </svg>
                      {t("app.deliverableOpen")}
                    </a>
                  ) : isProcessing ? (
                    <div className="d-flex align-items-center gap-2 text-muted small">
                      <div
                        className="spinner-border spinner-border-sm"
                        role="status"
                      >
                        <span className="visually-hidden">
                          {t("common.loading")}
                        </span>
                      </div>
                      {t("app.deliverableProcessing")}
                    </div>
                  ) : status.error ? (
                    <div>
                      <div className="small text-danger mb-1">
                        {status.error}
                      </div>
                      <button
                        type="button"
                        className="btn btn-sm btn-outline-secondary"
                        onClick={() => onRequest(value)}
                      >
                        {t("common.tryAgain")}
                      </button>
                    </div>
                  ) : (
                    <button
                      type="button"
                      className="btn btn-sm btn-outline-primary"
                      onClick={() => onRequest(value)}
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
  );
});

export default ScientificDeliverables;
