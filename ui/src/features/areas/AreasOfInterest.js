import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import BackButton from "../../components/BackButton";
import Pagination from "../../components/Pagination";
import { useLanguage } from "../../context/LanguageContext";
import useDebouncedSearch from "../../hooks/useDebouncedSearch";
import AreaFormModal from "./AreaFormModal";
import AreaTable from "./AreaTable";

function AreasOfInterest({ authorizedFetch, baseUrl, onBackToDashboard }) {
  const { t } = useLanguage();
  const [areas, setAreas] = useState([]);
  const [authorizedCountries, setAuthorizedCountries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const hasLoadedRef = useRef(false);
  const [error, setError] = useState(null);
  const [submitError, setSubmitError] = useState(null);
  const [submitSuccess, setSubmitSuccess] = useState(null);
  const [deleteConfirm, setDeleteConfirm] = useState(null);
  const [deleting, setDeleting] = useState(false);

  // Modal state
  const [modalMode, setModalMode] = useState(null); // null | "create" | "edit"
  const [editingArea, setEditingArea] = useState(null);

  // Kebab menu state
  const [openMenuId, setOpenMenuId] = useState(null);

  // Pagination and search state
  const [currentPage, setCurrentPage] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const [searchTerm, setSearchTerm] = useState("");
  const pageSize = 20;

  const loadAreas = useCallback(async (page = 1, search = "") => {
    if (!baseUrl) return;

    if (hasLoadedRef.current) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }
    setError(null);

    try {
      const params = new URLSearchParams({ page: page.toString() });
      if (search) {
        params.append("search", search);
      }

      const areasResponse = await authorizedFetch(
        `${baseUrl}/area_of_interest/?${params.toString()}`
      );
      if (areasResponse.ok) {
        const areasData = await areasResponse.json();
        setAreas(areasData.results || []);
        setTotalCount(areasData.count || 0);
        setCurrentPage(page);
      } else {
        throw new Error(t("areas.errorLoading"));
      }
    } catch (err) {
      console.error("Error loading areas:", err);
      setError(err.message);
    } finally {
      hasLoadedRef.current = true;
      setLoading(false);
      setRefreshing(false);
    }
  }, [authorizedFetch, baseUrl, t]);

  const loadAuthorizedCountries = useCallback(async () => {
    if (!baseUrl) return;

    try {
      const meResponse = await authorizedFetch(`${baseUrl}/me/`);
      if (meResponse.ok) {
        const meData = await meResponse.json();
        setAuthorizedCountries(meData.authorized_countries || []);
      }
    } catch (err) {
      console.error("Error loading authorized countries:", err);
    }
  }, [authorizedFetch, baseUrl]);

  const loadData = useCallback(async () => {
    await loadAuthorizedCountries();
    await loadAreas(1, "");
  }, [loadAuthorizedCountries, loadAreas]);

  useEffect(() => {
    loadAuthorizedCountries();
    loadAreas(1, "");
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSearch = useCallback((value) => {
    setSearchTerm(value);
    loadAreas(1, value);
  }, [loadAreas]);

  const { searchInput, handleSearchInput, clearSearch: handleClearSearch } =
    useDebouncedSearch(handleSearch);

  const totalPages = useMemo(() => {
    return Math.ceil(totalCount / pageSize);
  }, [totalCount, pageSize]);

  const handleDelete = useCallback(
    async (areaId) => {
      setDeleting(true);

      try {
        const response = await authorizedFetch(
          `${baseUrl}/area_of_interest/${areaId}/`,
          { method: "DELETE" }
        );

        if (!response.ok && response.status !== 204) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(errorData.error || t("areas.errorDeleting"));
        }

        setSubmitSuccess(t("areas.deleteSuccess"));
        setDeleteConfirm(null);
        loadAreas(currentPage, searchTerm);
      } catch (err) {
        console.error("Error deleting area:", err);
        setSubmitError(err.message);
      } finally {
        setDeleting(false);
      }
    },
    [authorizedFetch, baseUrl, currentPage, loadAreas, searchTerm, t]
  );

  const toggleMenu = useCallback((areaId) => {
    setOpenMenuId((prev) => (prev === areaId ? null : areaId));
  }, []);

  const closeMenu = useCallback(() => {
    setOpenMenuId(null);
  }, []);

  const openCreateModal = useCallback(() => {
    setModalMode("create");
    setEditingArea(null);
    setSubmitError(null);
  }, []);

  const openEditModal = useCallback((area) => {
    setModalMode("edit");
    setEditingArea(area);
    setSubmitError(null);
  }, []);

  const closeModal = useCallback(() => {
    setModalMode(null);
    setEditingArea(null);
  }, []);

  const handleModalSuccess = useCallback(
    (message) => {
      setSubmitSuccess(message);
      const page = modalMode === "edit" ? currentPage : 1;
      loadAreas(page, searchTerm);
    },
    [currentPage, loadAreas, modalMode, searchTerm]
  );

  if (loading && areas.length === 0) {
    return (
      <div className="d-flex justify-content-center align-items-center p-5">
        <div className="spinner-border text-primary" role="status">
          <span className="visually-hidden">{t("common.loading")}</span>
        </div>
      </div>
    );
  }

  if (error && areas.length === 0) {
    return (
      <div className="alert alert-danger m-4" role="alert">
        {error}
        <button
          type="button"
          className="btn btn-outline-danger btn-sm ms-3"
          onClick={loadData}
        >
          {t("common.tryAgain")}
        </button>
      </div>
    );
  }

  return (
    <div className="areas-management p-4">
      <div className="d-flex align-items-center justify-content-between mb-4 page-header-sticky">
        <h2 className="h4 mb-0">{t("areas.title")}</h2>
        <BackButton onClick={onBackToDashboard} />
      </div>

      {submitSuccess && (
        <div className="alert alert-success alert-dismissible fade show" role="alert">
          {submitSuccess}
          <button
            type="button"
            className="btn-close"
            onClick={() => setSubmitSuccess(null)}
            aria-label={t("common.close")}
          ></button>
        </div>
      )}
      {submitError && !modalMode && (
        <div className="alert alert-danger alert-dismissible fade show" role="alert">
          <div style={{ whiteSpace: "pre-wrap" }}>{submitError}</div>
          <button
            type="button"
            className="btn-close"
            onClick={() => setSubmitError(null)}
            aria-label={t("common.close")}
          ></button>
        </div>
      )}

      <div className="card shadow-sm widget-refresh-wrapper">
        {refreshing && (
          <div className="widget-refresh-overlay">
            <div className="spinner-border text-primary" role="status">
              <span className="visually-hidden">{t("common.loading")}</span>
            </div>
          </div>
        )}
        <div className="card-header">
          <div className="d-flex justify-content-between align-items-center mb-3">
            <h3 className="h5 mb-0">{t("areas.existingAreas")}</h3>
            <span className="badge bg-secondary">
              {totalCount} {t("areas.total")}
            </span>
          </div>
          <div className="search-input-wrapper position-relative">
            <input
              type="text"
              className="form-control"
              placeholder={t("areas.searchPlaceholder")}
              value={searchInput}
              onChange={(e) => handleSearchInput(e.target.value)}
            />
            {searchInput && (
              <button
                type="button"
                className="btn btn-link position-absolute end-0 top-50 translate-middle-y text-secondary p-0 pe-2"
                onClick={handleClearSearch}
                aria-label={t("areas.clearSearch")}
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="10" />
                  <line x1="15" y1="9" x2="9" y2="15" />
                  <line x1="9" y1="9" x2="15" y2="15" />
                </svg>
              </button>
            )}
          </div>
        </div>
        <div className="card-body p-0">
          <AreaTable
            areas={areas}
            deleteConfirm={deleteConfirm}
            setDeleteConfirm={setDeleteConfirm}
            deleting={deleting}
            handleDelete={handleDelete}
            openMenuId={openMenuId}
            toggleMenu={toggleMenu}
            closeMenu={closeMenu}
            openEditModal={openEditModal}
            t={t}
          />
        </div>
        <Pagination
          currentPage={currentPage}
          totalPages={totalPages}
          onPageChange={(page) => loadAreas(page, searchTerm)}
        />
      </div>

      {modalMode && (
        <AreaFormModal
          mode={modalMode}
          area={editingArea}
          authorizedFetch={authorizedFetch}
          baseUrl={baseUrl}
          authorizedCountries={authorizedCountries}
          onSuccess={handleModalSuccess}
          onClose={closeModal}
          t={t}
        />
      )}

      <button
        type="button"
        className="areas-fab"
        onClick={openCreateModal}
        aria-label={t("areas.addNew")}
        title={t("areas.addNew")}
      >
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
          <line x1="12" y1="5" x2="12" y2="19" />
          <line x1="5" y1="12" x2="19" y2="12" />
        </svg>
      </button>
    </div>
  );
}

export default AreasOfInterest;
