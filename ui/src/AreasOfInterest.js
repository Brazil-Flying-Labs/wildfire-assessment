import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useLanguage } from "./LanguageContext";

function AreasOfInterest({ authorizedFetch, baseUrl }) {
  const { t } = useLanguage();
  const [areas, setAreas] = useState([]);
  const [authorizedCountries, setAuthorizedCountries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [formData, setFormData] = useState({
    name: "",
    country: "",
  });
  const [geojsonFile, setGeojsonFile] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState(null);
  const [submitSuccess, setSubmitSuccess] = useState(null);
  const [deleteConfirm, setDeleteConfirm] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const fileInputRef = useRef(null);

  // Pagination and search state
  const [currentPage, setCurrentPage] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const [searchTerm, setSearchTerm] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const pageSize = 20;

  const loadAreas = useCallback(async (page = 1, search = "") => {
    if (!baseUrl) return;

    setLoading(true);
    setError(null);

    try {
      // Build query params
      const params = new URLSearchParams({ page: page.toString() });
      if (search) {
        params.append("search", search);
      }

      // Fetch areas with pagination
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
    await loadAreas(1, searchTerm);
  }, [loadAuthorizedCountries, loadAreas, searchTerm]);

  useEffect(() => {
    loadAuthorizedCountries();
  }, [loadAuthorizedCountries]);

  useEffect(() => {
    loadAreas(currentPage, searchTerm);
  }, [loadAreas, currentPage, searchTerm]);

  const handleSearch = useCallback((e) => {
    e.preventDefault();
    setSearchTerm(searchInput);
    setCurrentPage(1);
  }, [searchInput]);

  const handleClearSearch = useCallback(() => {
    setSearchInput("");
    setSearchTerm("");
    setCurrentPage(1);
  }, []);

  const totalPages = useMemo(() => {
    return Math.ceil(totalCount / pageSize);
  }, [totalCount, pageSize]);

  const handleInputChange = useCallback((e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  }, []);

  const handleFileChange = useCallback((e) => {
    const file = e.target.files?.[0];
    if (file) {
      setGeojsonFile(file);
    }
  }, []);

  const resetForm = useCallback(() => {
    setFormData({ name: "", country: "" });
    setGeojsonFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
    setSubmitError(null);
  }, []);

  const handleSubmit = useCallback(
    async (e) => {
      e.preventDefault();

      if (!formData.name || !formData.country || !geojsonFile) {
        setSubmitError(t("areas.fillAllFields"));
        return;
      }

      setSubmitting(true);
      setSubmitError(null);
      setSubmitSuccess(null);

      try {
        // Read and parse the GeoJSON file
        const fileContent = await new Promise((resolve, reject) => {
          const reader = new FileReader();
          reader.onload = (e) => resolve(e.target.result);
          reader.onerror = () => reject(new Error(t("areas.errorReadingFile")));
          reader.readAsText(geojsonFile);
        });

        let geojsonData;
        try {
          geojsonData = JSON.parse(fileContent);
        } catch (parseError) {
          throw new Error(t("areas.invalidGeojson"));
        }

        const payload = {
          name: formData.name,
          country: parseInt(formData.country, 10),
          geojson: geojsonData,
        };

        const response = await authorizedFetch(`${baseUrl}/area_of_interest/`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(payload),
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(
            errorData.detail ||
              errorData.error ||
              Object.values(errorData).flat().join(", ") ||
              t("areas.errorCreating")
          );
        }

        setSubmitSuccess(t("areas.createSuccess"));
        resetForm();
        loadAreas(1, searchTerm);
      } catch (err) {
        console.error("Error creating area:", err);
        setSubmitError(err.message);
      } finally {
        setSubmitting(false);
      }
    },
    [authorizedFetch, baseUrl, formData, geojsonFile, loadAreas, resetForm, searchTerm, t]
  );

  const handleDelete = useCallback(
    async (areaId) => {
      setDeleting(true);

      try {
        const response = await authorizedFetch(
          `${baseUrl}/area_of_interest/${areaId}/`,
          {
            method: "DELETE",
          }
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

  const isFormValid = useMemo(() => {
    return formData.name && formData.country && geojsonFile;
  }, [formData.name, formData.country, geojsonFile]);

  if (loading) {
    return (
      <div className="d-flex justify-content-center align-items-center p-5">
        <div className="spinner-border text-primary" role="status">
          <span className="visually-hidden">{t("common.loading")}</span>
        </div>
      </div>
    );
  }

  if (error) {
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
      <h2 className="h4 mb-4">{t("areas.title")}</h2>

      {/* Success/Error Messages */}
      {submitSuccess && (
        <div
          className="alert alert-success alert-dismissible fade show"
          role="alert"
        >
          {submitSuccess}
          <button
            type="button"
            className="btn-close"
            onClick={() => setSubmitSuccess(null)}
            aria-label={t("common.close")}
          ></button>
        </div>
      )}
      {submitError && (
        <div
          className="alert alert-danger alert-dismissible fade show"
          role="alert"
        >
          {submitError}
          <button
            type="button"
            className="btn-close"
            onClick={() => setSubmitError(null)}
            aria-label={t("common.close")}
          ></button>
        </div>
      )}

      {/* Create Form */}
      <div className="card shadow-sm mb-4">
        <div className="card-header">
          <h3 className="h5 mb-0">{t("areas.createNew")}</h3>
        </div>
        <div className="card-body">
          <form onSubmit={handleSubmit}>
            <div className="row g-3">
              <div className="col-md-4">
                <label htmlFor="areaName" className="form-label">
                  {t("areas.name")} *
                </label>
                <input
                  type="text"
                  className="form-control"
                  id="areaName"
                  name="name"
                  value={formData.name}
                  onChange={handleInputChange}
                  placeholder={t("areas.namePlaceholder")}
                  required
                />
              </div>

              <div className="col-md-4">
                <label htmlFor="areaCountry" className="form-label">
                  {t("areas.country")} *
                </label>
                <select
                  className="form-select"
                  id="areaCountry"
                  name="country"
                  value={formData.country}
                  onChange={handleInputChange}
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

              <div className="col-md-4">
                <label htmlFor="areaGeojson" className="form-label">
                  {t("areas.geojsonFile")} *
                </label>
                <input
                  type="file"
                  className="form-control"
                  id="areaGeojson"
                  ref={fileInputRef}
                  accept=".geojson,.json"
                  onChange={handleFileChange}
                  required
                />
                <div className="form-text">{t("areas.geojsonHint")}</div>
              </div>
            </div>

            <div className="mt-3 d-flex gap-2 form-buttons">
              <button
                type="submit"
                className="btn btn-primary"
                disabled={submitting || !isFormValid}
              >
                {submitting ? (
                  <>
                    <span
                      className="spinner-border spinner-border-sm me-2"
                      role="status"
                      aria-hidden="true"
                    ></span>
                    {t("areas.creating")}
                  </>
                ) : (
                  t("areas.create")
                )}
              </button>
              <button
                type="button"
                className="btn btn-outline-secondary"
                onClick={resetForm}
                disabled={submitting}
              >
                {t("areas.reset")}
              </button>
            </div>
          </form>
        </div>
      </div>

      {/* Areas Table */}
      <div className="card shadow-sm">
        <div className="card-header">
          <div className="d-flex justify-content-between align-items-center mb-3">
            <h3 className="h5 mb-0">{t("areas.existingAreas")}</h3>
            <span className="badge bg-secondary">
              {totalCount} {t("areas.total")}
            </span>
          </div>
          {/* Search Bar */}
          <form onSubmit={handleSearch} className="d-flex gap-2">
            <input
              type="text"
              className="form-control"
              placeholder={t("areas.searchPlaceholder")}
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
            />
            <button type="submit" className="btn btn-outline-primary">
              {t("areas.search")}
            </button>
            {searchTerm && (
              <button
                type="button"
                className="btn btn-outline-secondary"
                onClick={handleClearSearch}
              >
                {t("areas.clearSearch")}
              </button>
            )}
          </form>
        </div>
        <div className="card-body p-0">
          {areas.length === 0 ? (
            <div className="p-4 text-center text-muted">
              {t("areas.noAreas")}
            </div>
          ) : (
            <div className="table-responsive">
              <table className="table table-hover mb-0">
                <thead className="table-light">
                  <tr>
                    <th scope="col">{t("areas.name")}</th>
                    <th scope="col">{t("areas.country")}</th>
                    <th scope="col">{t("areas.areaHa")}</th>
                    <th scope="col">{t("areas.municipality")}</th>
                    <th scope="col" className="text-end">
                      {t("areas.actions")}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {areas.map((area) => (
                    <tr key={area.id}>
                      <td>
                        <strong>{area.name}</strong>
                      </td>
                      <td>
                        {area.country_name
                          ? `${area.country_name} (${area.country_code})`
                          : "-"}
                      </td>
                      <td>
                        {area.area_ha
                          ? parseFloat(area.area_ha).toLocaleString("pt-BR", {
                              minimumFractionDigits: 2,
                              maximumFractionDigits: 2,
                            })
                          : "-"}
                      </td>
                      <td>{area.municipio || "-"}</td>
                      <td className="text-end">
                        {deleteConfirm === area.id ? (
                          <div className="btn-group btn-group-sm">
                            <button
                              type="button"
                              className="btn btn-danger"
                              onClick={() => handleDelete(area.id)}
                              disabled={deleting}
                            >
                              {deleting ? (
                                <span
                                  className="spinner-border spinner-border-sm"
                                  role="status"
                                  aria-hidden="true"
                                ></span>
                              ) : (
                                t("areas.confirmDelete")
                              )}
                            </button>
                            <button
                              type="button"
                              className="btn btn-outline-secondary"
                              onClick={() => setDeleteConfirm(null)}
                              disabled={deleting}
                            >
                              {t("areas.cancel")}
                            </button>
                          </div>
                        ) : (
                          <button
                            type="button"
                            className="btn btn-outline-danger btn-sm"
                            onClick={() => setDeleteConfirm(area.id)}
                            title={t("areas.delete")}
                          >
                            {t("areas.delete")}
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
        {/* Pagination */}
        {totalPages > 1 && (
          <div className="card-footer d-flex justify-content-between align-items-center">
            <div className="text-muted small">
              {t("areas.showing")} {(currentPage - 1) * pageSize + 1}-
              {Math.min(currentPage * pageSize, totalCount)} {t("areas.of")}{" "}
              {totalCount}
            </div>
            <nav aria-label={t("areas.pagination")}>
              <ul className="pagination pagination-sm mb-0">
                <li
                  className={`page-item ${currentPage === 1 ? "disabled" : ""}`}
                >
                  <button
                    className="page-link"
                    onClick={() => setCurrentPage(1)}
                    disabled={currentPage === 1}
                  >
                    &laquo;
                  </button>
                </li>
                <li
                  className={`page-item ${currentPage === 1 ? "disabled" : ""}`}
                >
                  <button
                    className="page-link"
                    onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                    disabled={currentPage === 1}
                  >
                    &lsaquo;
                  </button>
                </li>
                {/* Page numbers */}
                {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                  let pageNum;
                  if (totalPages <= 5) {
                    pageNum = i + 1;
                  } else if (currentPage <= 3) {
                    pageNum = i + 1;
                  } else if (currentPage >= totalPages - 2) {
                    pageNum = totalPages - 4 + i;
                  } else {
                    pageNum = currentPage - 2 + i;
                  }
                  return (
                    <li
                      key={pageNum}
                      className={`page-item ${
                        currentPage === pageNum ? "active" : ""
                      }`}
                    >
                      <button
                        className="page-link"
                        onClick={() => setCurrentPage(pageNum)}
                      >
                        {pageNum}
                      </button>
                    </li>
                  );
                })}
                <li
                  className={`page-item ${
                    currentPage === totalPages ? "disabled" : ""
                  }`}
                >
                  <button
                    className="page-link"
                    onClick={() =>
                      setCurrentPage((p) => Math.min(totalPages, p + 1))
                    }
                    disabled={currentPage === totalPages}
                  >
                    &rsaquo;
                  </button>
                </li>
                <li
                  className={`page-item ${
                    currentPage === totalPages ? "disabled" : ""
                  }`}
                >
                  <button
                    className="page-link"
                    onClick={() => setCurrentPage(totalPages)}
                    disabled={currentPage === totalPages}
                  >
                    &raquo;
                  </button>
                </li>
              </ul>
            </nav>
          </div>
        )}
      </div>
    </div>
  );
}

export default AreasOfInterest;
