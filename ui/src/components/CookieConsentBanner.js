import { useLanguage } from "../context/LanguageContext";
import useCookieConsent from "../hooks/useCookieConsent";
import "./CookieConsentBanner.css";

function CookieConsentBanner() {
  const { t } = useLanguage();
  const { consent, acceptCookies, rejectCookies } = useCookieConsent();

  if (consent) return null;

  return (
    <div className="cookie-banner" role="dialog" aria-label={t("cookies.title")}>
      <div className="cookie-banner-content">
        <div className="cookie-banner-text">
          <strong>{t("cookies.title")}</strong>
          <p>{t("cookies.description")}</p>
          <p>{t("cookies.optionalNotice")}</p>
          <p>
            {t("cookies.acceptExplanation")}
            <br />
            {t("cookies.rejectExplanation")}
          </p>
          <p className="cookie-banner-settings-hint">
            {t("cookies.settingsHint")}
          </p>
        </div>
        <div className="cookie-banner-actions">
          <button
            type="button"
            className="btn btn-primary btn-sm"
            onClick={acceptCookies}
          >
            {t("cookies.accept")}
          </button>
          <button
            type="button"
            className="btn btn-outline-secondary btn-sm"
            onClick={rejectCookies}
          >
            {t("cookies.reject")}
          </button>
        </div>
      </div>
    </div>
  );
}

export default CookieConsentBanner;
