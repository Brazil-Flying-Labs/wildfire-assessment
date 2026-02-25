import { useCallback, useState } from "react";
import { useLanguage } from "../../context/LanguageContext";
import TermsContent from "./TermsContent";

function TermsPage({ logoSrc, onAccept, onLogout }) {
  const { t } = useLanguage();
  const [accepting, setAccepting] = useState(false);
  const [declined, setDeclined] = useState(false);

  const handleAccept = useCallback(async () => {
    setAccepting(true);
    try {
      await onAccept();
    } finally {
      setAccepting(false);
    }
  }, [onAccept]);

  if (declined) {
    return (
      <div className="app-root d-flex align-items-center justify-content-center min-vh-100">
        <div className="text-center p-4">
          <img src={logoSrc} alt="" className="brand-logo mb-4" />
          <h2>{t("terms.title")}</h2>
          <p className="text-muted mt-3">{t("terms.declinedMessage")}</p>
          <div className="terms-actions mt-4">
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => setDeclined(false)}
            >
              {t("terms.reviewTerms")}
            </button>
            <button
              type="button"
              className="btn btn-outline-secondary"
              onClick={onLogout}
            >
              {t("common.logout")}
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="app-root d-flex align-items-center justify-content-center min-vh-100">
      <div className="terms-page">
        <div className="text-center mb-4">
          <img src={logoSrc} alt="" className="brand-logo mb-3" />
          <h2>{t("terms.title")}</h2>
        </div>

        <div className="terms-content">
          <TermsContent />
        </div>

        <div className="terms-actions">
          <button
            type="button"
            className="btn btn-primary"
            onClick={handleAccept}
            disabled={accepting}
          >
            {accepting ? (
              <>
                <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                {t("terms.accept")}
              </>
            ) : (
              t("terms.accept")
            )}
          </button>
          <button
            type="button"
            className="btn btn-outline-secondary"
            onClick={() => setDeclined(true)}
            disabled={accepting}
          >
            {t("terms.decline")}
          </button>
        </div>
      </div>
    </div>
  );
}

export default TermsPage;
