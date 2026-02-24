import { useLanguage } from "../context/LanguageContext";

const PAGE_LABELS = {
  dashboard: "nav.dashboard",
  analysis: "nav.analysis",
  areas: "nav.areas",
  profile: "nav.profile",
  "analysis-detail": "nav.analysisDetail",
};

function Breadcrumbs({ currentPage, navigateTo }) {
  const { t } = useLanguage();

  if (currentPage === "dashboard") return null;

  return (
    <nav aria-label="Breadcrumb" className="breadcrumbs no-print">
      <button
        type="button"
        className="breadcrumb-link"
        onClick={() => navigateTo("dashboard")}
      >
        {t("nav.dashboard")}
      </button>
      <span className="breadcrumb-separator" aria-hidden="true">›</span>
      <span className="breadcrumb-current">
        {t(PAGE_LABELS[currentPage] || currentPage)}
      </span>
    </nav>
  );
}

export default Breadcrumbs;
