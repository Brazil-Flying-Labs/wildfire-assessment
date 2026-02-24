import { useLanguage } from "../context/LanguageContext";

function BackButton({ onClick, className = "no-print" }) {
  const { t } = useLanguage();

  return (
    <button
      type="button"
      className={`btn btn-outline-secondary btn-sm d-flex align-items-center gap-1 ${className}`}
      onClick={onClick}
      title={t("common.back")}
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
        <line x1="19" y1="12" x2="5" y2="12" />
        <polyline points="12 19 5 12 12 5" />
      </svg>
      {t("common.back")}
    </button>
  );
}

export default BackButton;
