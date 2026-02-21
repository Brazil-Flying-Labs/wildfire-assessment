import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useLanguage } from "./LanguageContext";

function AreasOfInterest({ authorizedFetch, baseUrl, onBackToDashboard }) {
  const { t } = useLanguage();
  const [areas, setAreas] = useState([]);
  const [authorizedCountries, setAuthorizedCountries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [submitError, setSubmitError] = useState(null);
  const [submitSuccess, setSubmitSuccess] = useState(null);
  const [deleteConfirm, setDeleteConfirm] = useState(null);
  const [deleting, setDeleting] = useState(false);

  // Create modal state
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [createFormData, setCreateFormData] = useState({ name: "", country: "" });
  const [createGeojsonFile, setCreateGeojsonFile] = useState(null);
  const [createSubmitting, setCreateSubmitting] = useState(false);
  const createFileInputRef = useRef(null);

  // Edit modal state
  const [editingArea, setEditingArea] = useState(null);
  const [editFormData, setEditFormData] = useState({ name: "", country: "" });
  const [editGeojsonFile, setEditGeojsonFile] = useState(null);
  const [editSubmitting, setEditSubmitting] = useState(false);
  const editFileInputRef = useRef(null);

  // Kebab menu state
  const [openMenuId, setOpenMenuId] = useState(null);

  // Pagination and search state
  const [currentPage, setCurrentPage] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const [searchTerm, setSearchTerm] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const searchDebounceRef = useRef(null);
  const pageSize = 20;

  const loadAreas = useCallback(async (page = 1, search = "") => {
    if (!baseUrl) return;

    setLoading(true);
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
      setLoading(false);
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

  // Debounced search handler
  const handleSearchInput = useCallback((value) => {
    setSearchInput(value);

    // Clear existing debounce timer
    if (searchDebounceRef.current) {
      clearTimeout(searchDebounceRef.current);
    }

    // Search if 2+ characters or empty (to show all)
    searchDebounceRef.current = setTimeout(() => {
      if (value.length >= 2 || value.length === 0) {
        setSearchTerm(value);
        loadAreas(1, value);
      }
    }, 300);
  }, [loadAreas]);

  // Cleanup debounce timer on unmount
  useEffect(() => {
    return () => {
      if (searchDebounceRef.current) {
        clearTimeout(searchDebounceRef.current);
      }
    };
  }, []);

  const handleClearSearch = useCallback(() => {
    setSearchInput("");
    setSearchTerm("");
    if (searchDebounceRef.current) {
      clearTimeout(searchDebounceRef.current);
    }
    loadAreas(1, "");
  }, [loadAreas]);

  const totalPages = useMemo(() => {
    return Math.ceil(totalCount / pageSize);
  }, [totalCount, pageSize]);

  // Format error messages from API response
  const formatApiErrors = useCallback((errorData) => {
    let errorMessage = errorData.detail || errorData.error;
    
    if (!errorMessage && typeof errorData === "object") {
      const errorParts = [];
      for (const [field, errors] of Object.entries(errorData)) {
        const errorList = Array.isArray(errors) ? errors : [errors];
        const fieldLabel = field === "geojson" ? t("areas.geojsonFile") : field;
        errorParts.push(`${fieldLabel}: ${errorList.join(", ")}`);
      }
      errorMessage = errorParts.join("\n");
    }
    
    return errorMessage;
  }, [t]);

  const validatePolygonGeometry = useCallback((geojson) => {
    const allowed = ["Polygon", "MultiPolygon"];
    const type = geojson.type;
    if (type === "Feature") {
      const geomType = geojson.geometry?.type;
      if (!allowed.includes(geomType)) return false;
    } else if (type === "FeatureCollection") {
      for (const feat of geojson.features || []) {
        const geomType = feat.geometry?.type;
        if (!allowed.includes(geomType)) return false;
      }
    } else if (!allowed.includes(type)) {
      return false;
    }
    return true;
  }, []);

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

  // Kebab menu handlers
  const toggleMenu = useCallback((areaId) => {
    setOpenMenuId((prev) => (prev === areaId ? null : areaId));
  }, []);

  const closeMenu = useCallback(() => {
    setOpenMenuId(null);
  }, []);

  // Create modal handlers
  const openCreateModal = useCallback(() => {
    setShowCreateModal(true);
    setCreateFormData({ name: "", country: "" });
    setCreateGeojsonFile(null);
    setSubmitError(null);
  }, []);

  const closeCreateModal = useCallback(() => {
    setShowCreateModal(false);
    setCreateFormData({ name: "", country: "" });
    setCreateGeojsonFile(null);
    if (createFileInputRef.current) {
      createFileInputRef.current.value = "";
    }
  }, []);

  const handleCreateInputChange = useCallback((e) => {
    const { name, value } = e.target;
    setCreateFormData((prev) => ({ ...prev, [name]: value }));
  }, []);

  const handleCreateFileChange = useCallback((e) => {
    const file = e.target.files?.[0];
    if (file) {
      setCreateGeojsonFile(file);
    }
  }, []);

  const handleCreateSubmit = useCallback(
    async (e) => {
      e.preventDefault();

      if (!createFormData.name || !createFormData.country || !createGeojsonFile) {
        setSubmitError(t("areas.fillAllFields"));
        return;
      }

      setCreateSubmitting(true);
      setSubmitError(null);
      setSubmitSuccess(null);

      try {
        const fileContent = await new Promise((resolve, reject) => {
          const reader = new FileReader();
          reader.onload = (e) => resolve(e.target.result);
          reader.onerror = () => reject(new Error(t("areas.errorReadingFile")));
          reader.readAsText(createGeojsonFile);
        });

        let geojsonData;
        try {
          geojsonData = JSON.parse(fileContent);
        } catch (parseError) {
          throw new Error(t("areas.invalidGeojson"));
        }

        if (!validatePolygonGeometry(geojsonData)) {
          throw new Error(t("areas.polygonRequired"));
        }

        const payload = {
          name: createFormData.name,
          country: parseInt(createFormData.country, 10),
          geojson: geojsonData,
        };

        const response = await authorizedFetch(`${baseUrl}/area_of_interest/`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(formatApiErrors(errorData) || t("areas.errorCreating"));
        }

        setSubmitSuccess(t("areas.createSuccess"));
        closeCreateModal();
        loadAreas(1, searchTerm);
      } catch (err) {
        console.error("Error creating area:", err);
        setSubmitError(err.message);
      } finally {
        setCreateSubmitting(false);
      }
    },
    [authorizedFetch, baseUrl, closeCreateModal, createFormData, createGeojsonFile, formatApiErrors, loadAreas, searchTerm, t, validatePolygonGeometry]
  );

  // Edit modal handlers
  const openEditModal = useCallback((area) => {
    setEditingArea(area);
    setEditFormData({
      name: area.name,
      country: area.country?.toString() || "",
    });
    setEditGeojsonFile(null);
    setSubmitError(null);
  }, []);

  const closeEditModal = useCallback(() => {
    setEditingArea(null);
    setEditFormData({ name: "", country: "" });
    setEditGeojsonFile(null);
    if (editFileInputRef.current) {
      editFileInputRef.current.value = "";
    }
  }, []);

  const handleEditInputChange = useCallback((e) => {
    const { name, value } = e.target;
    setEditFormData((prev) => ({ ...prev, [name]: value }));
  }, []);

  const handleEditFileChange = useCallback((e) => {
    const file = e.target.files?.[0];
    if (file) {
      setEditGeojsonFile(file);
    }
  }, []);

  const handleEditSubmit = useCallback(
    async (e) => {
      e.preventDefault();

      if (!editFormData.name) {
        setSubmitError(t("areas.fillAllFields"));
        return;
      }

      setEditSubmitting(true);
      setSubmitError(null);
      setSubmitSuccess(null);

      try {
        const payload = {
          name: editFormData.name,
        };

        if (editFormData.country) {
          payload.country = parseInt(editFormData.country, 10);
        }

        if (editGeojsonFile) {
          const fileContent = await new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = (e) => resolve(e.target.result);
            reader.onerror = () => reject(new Error(t("areas.errorReadingFile")));
            reader.readAsText(editGeojsonFile);
          });

          let geojsonData;
          try {
            geojsonData = JSON.parse(fileContent);
          } catch (parseError) {
            throw new Error(t("areas.invalidGeojson"));
          }

          if (!validatePolygonGeometry(geojsonData)) {
            throw new Error(t("areas.polygonRequired"));
          }
          payload.geojson = geojsonData;
        }

        const response = await authorizedFetch(
          `${baseUrl}/area_of_interest/${editingArea.id}/`,
          {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
          }
        );

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(formatApiErrors(errorData) || t("areas.errorUpdating"));
        }

        setSubmitSuccess(t("areas.updateSuccess"));
        closeEditModal();
        loadAreas(currentPage, searchTerm);
      } catch (err) {
        console.error("Error updating area:", err);
        setSubmitError(err.message);
      } finally {
        setEditSubmitting(false);
      }
    },
    [authorizedFetch, baseUrl, closeEditModal, currentPage, editFormData, editGeojsonFile, editingArea, formatApiErrors, loadAreas, searchTerm, t, validatePolygonGeometry]
  );

  const isCreateFormValid = useMemo(() => {
    return createFormData.name && createFormData.country && createGeojsonFile;
  }, [createFormData.name, createFormData.country, createGeojsonFile]);

  const isEditFormValid = useMemo(() => {
    return editFormData.name;
  }, [editFormData.name]);

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
      <div className="d-flex align-items-center justify-content-between mb-4">
        <h2 className="h4 mb-0">{t("areas.title")}</h2>
        <button
          type="button"
          className="btn btn-link text-decoration-none p-0 no-print"
          onClick={onBackToDashboard}
        >
          ← {t("analysisDetail.backToDashboard")}
        </button>
      </div>

      {/* Success/Error Messages */}
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
      {submitError && !showCreateModal && !editingArea && (
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

      {/* Areas Table */}
      <div className="card shadow-sm">
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
          {areas.length === 0 ? (
            <div className="p-4 text-center text-muted">
              {t("areas.noAreas")}
            </div>
          ) : (
            <>
              {/* Desktop table */}
              <div className="table-responsive d-none d-md-block">
                <table className="table table-hover mb-0 areas-table">
                  <thead className="table-light">
                    <tr>
                      <th scope="col">{t("areas.name")}</th>
                      <th scope="col">{t("areas.country")}</th>
                      <th scope="col" className="text-end" style={{ width: "50px" }}>
                        <span className="visually-hidden">{t("areas.actions")}</span>
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {areas.map((area) => (
                      <tr key={area.id}>
                        <td><strong>{area.name}</strong></td>
                        <td>
                          {area.country_name
                            ? `${area.country_name} (${area.country_code})`
                            : "-"}
                        </td>
                        <td className="text-end">
                          {deleteConfirm === area.id ? (
                            <div className="d-flex gap-1 justify-content-end">
                              <button
                                type="button"
                                className="btn btn-danger btn-sm"
                                onClick={() => handleDelete(area.id)}
                                disabled={deleting}
                              >
                                {deleting ? (
                                  <span className="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
                                ) : (
                                  t("areas.confirmDelete")
                                )}
                              </button>
                              <button
                                type="button"
                                className="btn btn-outline-secondary btn-sm"
                                onClick={() => setDeleteConfirm(null)}
                                disabled={deleting}
                              >
                                {t("areas.cancel")}
                              </button>
                            </div>
                          ) : (
                            <div className="kebab-menu">
                              <button
                                type="button"
                                className="btn btn-link text-secondary p-1 kebab-trigger"
                                onClick={() => toggleMenu(area.id)}
                                aria-label={t("areas.actions")}
                              >
                                <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                                  <circle cx="12" cy="5" r="2" />
                                  <circle cx="12" cy="12" r="2" />
                                  <circle cx="12" cy="19" r="2" />
                                </svg>
                              </button>
                              {openMenuId === area.id && (
                                <>
                                  <div className="kebab-backdrop" onClick={closeMenu}></div>
                                  <div className="kebab-dropdown">
                                    <button
                                      type="button"
                                      className="kebab-item"
                                      onClick={() => {
                                        closeMenu();
                                        openEditModal(area);
                                      }}
                                    >
                                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                        <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                                        <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
                                      </svg>
                                      {t("areas.edit")}
                                    </button>
                                    <button
                                      type="button"
                                      className="kebab-item text-danger"
                                      onClick={() => {
                                        closeMenu();
                                        setDeleteConfirm(area.id);
                                      }}
                                    >
                                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                        <polyline points="3 6 5 6 21 6" />
                                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                                      </svg>
                                      {t("areas.delete")}
                                    </button>
                                  </div>
                                </>
                              )}
                            </div>
                          )}
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
                        <span className="text-muted small">
                          {area.country_name
                            ? `${area.country_name} (${area.country_code})`
                            : "-"}
                        </span>
                      </div>
                      <div className="mobile-card-actions">
                        {deleteConfirm === area.id ? (
                          <div className="d-flex gap-1">
                            <button
                              type="button"
                              className="btn btn-danger btn-sm"
                              onClick={() => handleDelete(area.id)}
                              disabled={deleting}
                            >
                              {deleting ? (
                                <span className="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
                              ) : (
                                t("areas.confirmDelete")
                              )}
                            </button>
                            <button
                              type="button"
                              className="btn btn-outline-secondary btn-sm"
                              onClick={() => setDeleteConfirm(null)}
                              disabled={deleting}
                            >
                              {t("areas.cancel")}
                            </button>
                          </div>
                        ) : (
                          <div className="kebab-menu">
                            <button
                              type="button"
                              className="btn btn-link text-secondary p-1 kebab-trigger"
                              onClick={() => toggleMenu(area.id)}
                              aria-label={t("areas.actions")}
                            >
                              <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                                <circle cx="12" cy="5" r="2" />
                                <circle cx="12" cy="12" r="2" />
                                <circle cx="12" cy="19" r="2" />
                              </svg>
                            </button>
                            {openMenuId === area.id && (
                              <>
                                <div className="kebab-backdrop" onClick={closeMenu}></div>
                                <div className="kebab-dropdown">
                                  <button
                                    type="button"
                                    className="kebab-item"
                                    onClick={() => {
                                      closeMenu();
                                      openEditModal(area);
                                    }}
                                  >
                                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                      <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                                      <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
                                    </svg>
                                    {t("areas.edit")}
                                  </button>
                                  <button
                                    type="button"
                                    className="kebab-item text-danger"
                                    onClick={() => {
                                      closeMenu();
                                      setDeleteConfirm(area.id);
                                    }}
                                  >
                                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                      <polyline points="3 6 5 6 21 6" />
                                      <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                                    </svg>
                                    {t("areas.delete")}
                                  </button>
                                </div>
                              </>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
        {/* Pagination */}
        {totalPages > 1 && (
          <div className="card-footer">
            <div className="areas-pagination">
              <button
                type="button"
                className="areas-pagination-btn"
                onClick={() => loadAreas(currentPage - 1, searchTerm)}
                disabled={currentPage === 1}
                aria-label={t("areas.prevPage")}
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="15 18 9 12 15 6" />
                </svg>
              </button>
              <span className="areas-pagination-info">
                {currentPage} / {totalPages}
              </span>
              <button
                type="button"
                className="areas-pagination-btn"
                onClick={() => loadAreas(currentPage + 1, searchTerm)}
                disabled={currentPage === totalPages}
                aria-label={t("areas.nextPage")}
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="9 18 15 12 9 6" />
                </svg>
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Create Modal */}
      {showCreateModal && (
        <>
          <div className="modal-backdrop fade show" onClick={closeCreateModal}></div>
          <div className="modal fade show d-block" tabIndex="-1" role="dialog">
            <div className="modal-dialog modal-dialog-centered" role="document">
              <div className="modal-content">
                <div className="modal-header">
                  <h5 className="modal-title">{t("areas.addNewArea")}</h5>
                  <button
                    type="button"
                    className="btn-close"
                    onClick={closeCreateModal}
                    aria-label={t("common.close")}
                  ></button>
                </div>
                <form onSubmit={handleCreateSubmit}>
                  <div className="modal-body">
                    {submitError && (
                      <div className="alert alert-danger" role="alert">
                        <div style={{ whiteSpace: "pre-wrap" }}>{submitError}</div>
                      </div>
                    )}
                    <div className="mb-3">
                      <label htmlFor="createAreaName" className="form-label">
                        {t("areas.name")} *
                      </label>
                      <input
                        type="text"
                        className="form-control"
                        id="createAreaName"
                        name="name"
                        value={createFormData.name}
                        onChange={handleCreateInputChange}
                        placeholder={t("areas.namePlaceholder")}
                        required
                      />
                    </div>

                    <div className="mb-3">
                      <label htmlFor="createAreaCountry" className="form-label">
                        {t("areas.country")} *
                      </label>
                      <select
                        className="form-select"
                        id="createAreaCountry"
                        name="country"
                        value={createFormData.country}
                        onChange={handleCreateInputChange}
                        required
                      >
                        <option value="">{t("areas.selectCountry")}</option>
                        {authorizedCountries.map((country) => (
                          <option key={country.id} value={country.id}>
                            {country.name} ({country.code})
                          </option>
                        ))}
                      </select>
                      {authorizedCountries.length === 0 && (
                        <div className="form-text text-warning">
                          {t("areas.noCountries")}
                        </div>
                      )}
                    </div>

                    <div className="mb-3">
                      <label htmlFor="createAreaGeojson" className="form-label">
                        {t("areas.geojsonFile")} *
                      </label>
                      <input
                        type="file"
                        className="form-control"
                        id="createAreaGeojson"
                        ref={createFileInputRef}
                        accept=".geojson,.json"
                        onChange={handleCreateFileChange}
                        required
                      />
                      <div className="form-text">{t("areas.geojsonHint")}</div>
                    </div>
                  </div>
                  <div className="modal-footer">
                    <button
                      type="button"
                      className="btn btn-secondary"
                      onClick={closeCreateModal}
                      disabled={createSubmitting}
                    >
                      {t("areas.cancel")}
                    </button>
                    <button
                      type="submit"
                      className="btn btn-primary"
                      disabled={createSubmitting || !isCreateFormValid}
                    >
                      {createSubmitting ? (
                        <>
                          <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                          {t("areas.creating")}
                        </>
                      ) : (
                        t("areas.create")
                      )}
                    </button>
                  </div>
                </form>
              </div>
            </div>
          </div>
        </>
      )}

      {/* Edit Modal */}
      {editingArea && (
        <>
          <div className="modal-backdrop fade show" onClick={closeEditModal}></div>
          <div className="modal fade show d-block" tabIndex="-1" role="dialog">
            <div className="modal-dialog modal-dialog-centered" role="document">
              <div className="modal-content">
                <div className="modal-header">
                  <h5 className="modal-title">{t("areas.editArea")}</h5>
                  <button
                    type="button"
                    className="btn-close"
                    onClick={closeEditModal}
                    aria-label={t("common.close")}
                  ></button>
                </div>
                <form onSubmit={handleEditSubmit}>
                  <div className="modal-body">
                    {submitError && (
                      <div className="alert alert-danger" role="alert">
                        <div style={{ whiteSpace: "pre-wrap" }}>{submitError}</div>
                      </div>
                    )}
                    <div className="mb-3">
                      <label htmlFor="editAreaName" className="form-label">
                        {t("areas.name")} *
                      </label>
                      <input
                        type="text"
                        className="form-control"
                        id="editAreaName"
                        name="name"
                        value={editFormData.name}
                        onChange={handleEditInputChange}
                        placeholder={t("areas.namePlaceholder")}
                        required
                      />
                    </div>

                    <div className="mb-3">
                      <label htmlFor="editAreaCountry" className="form-label">
                        {t("areas.country")}
                      </label>
                      <select
                        className="form-select"
                        id="editAreaCountry"
                        name="country"
                        value={editFormData.country}
                        onChange={handleEditInputChange}
                      >
                        <option value="">{t("areas.keepCurrent")}</option>
                        {authorizedCountries.map((country) => (
                          <option key={country.id} value={country.id}>
                            {country.name} ({country.code})
                          </option>
                        ))}
                      </select>
                    </div>

                    <div className="mb-3">
                      <label htmlFor="editAreaGeojson" className="form-label">
                        {t("areas.geojsonFile")}
                      </label>
                      <input
                        type="file"
                        className="form-control"
                        id="editAreaGeojson"
                        ref={editFileInputRef}
                        accept=".geojson,.json"
                        onChange={handleEditFileChange}
                      />
                      <div className="form-text">{t("areas.geojsonOptionalHint")}</div>
                    </div>
                  </div>
                  <div className="modal-footer">
                    <button
                      type="button"
                      className="btn btn-secondary"
                      onClick={closeEditModal}
                      disabled={editSubmitting}
                    >
                      {t("areas.cancel")}
                    </button>
                    <button
                      type="submit"
                      className="btn btn-primary"
                      disabled={editSubmitting || !isEditFormValid}
                    >
                      {editSubmitting ? (
                        <>
                          <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                          {t("areas.saving")}
                        </>
                      ) : (
                        t("areas.save")
                      )}
                    </button>
                  </div>
                </form>
              </div>
            </div>
          </div>
        </>
      )}

      {/* Floating Action Button */}
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
