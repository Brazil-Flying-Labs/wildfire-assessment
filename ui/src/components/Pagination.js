import { useLanguage } from "../context/LanguageContext";

function Pagination({ currentPage, totalPages, onPageChange }) {
  const { t } = useLanguage();

  if (totalPages <= 1) return null;

  return (
    <div className="card-footer">
      <div className="areas-pagination">
        <button
          type="button"
          className="areas-pagination-btn"
          onClick={() => onPageChange(currentPage - 1)}
          disabled={currentPage === 1}
          aria-label={t("areas.prevPage")}
        >
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <polyline points="15 18 9 12 15 6" />
          </svg>
        </button>
        <span className="areas-pagination-info">
          {currentPage} / {totalPages}
        </span>
        <button
          type="button"
          className="areas-pagination-btn"
          onClick={() => onPageChange(currentPage + 1)}
          disabled={currentPage === totalPages}
          aria-label={t("areas.nextPage")}
        >
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <polyline points="9 18 15 12 9 6" />
          </svg>
        </button>
      </div>
    </div>
  );
}

export default Pagination;
