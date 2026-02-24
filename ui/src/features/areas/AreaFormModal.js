import { useCallback, useMemo, useRef, useState } from "react";
import { formatApiErrors } from "../../utils/apiErrors";
import { validatePolygonGeometry } from "../../utils/geojson";
import { readFileAsText } from "../../utils/fileReader";

function AreaFormModal({
  mode,
  area,
  authorizedFetch,
  baseUrl,
  authorizedCountries,
  onSuccess,
  onClose,
  t,
}) {
  const isEdit = mode === "edit";
  const [formData, setFormData] = useState({
    name: isEdit ? area?.name || "" : "",
    country: isEdit ? area?.country?.toString() || "" : "",
  });
  const [geojsonFile, setGeojsonFile] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const fileInputRef = useRef(null);

  const handleInputChange = useCallback((e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  }, []);

  const handleFileChange = useCallback((e) => {
    const file = e.target.files?.[0];
    if (file) setGeojsonFile(file);
  }, []);

  const isFormValid = useMemo(() => {
    if (isEdit) return !!formData.name;
    return formData.name && formData.country && geojsonFile;
  }, [isEdit, formData.name, formData.country, geojsonFile]);

  const handleSubmit = useCallback(
    async (e) => {
      e.preventDefault();

      if (!isEdit && (!formData.name || !formData.country || !geojsonFile)) {
        setError(t("areas.fillAllFields"));
        return;
      }
      if (isEdit && !formData.name) {
        setError(t("areas.fillAllFields"));
        return;
      }

      setSubmitting(true);
      setError(null);

      try {
        const payload = { name: formData.name };

        if (formData.country) {
          payload.country = parseInt(formData.country, 10);
        }

        const fileToValidate = geojsonFile;
        if (fileToValidate || !isEdit) {
          const fileContent = await readFileAsText(
            fileToValidate,
            t("areas.errorReadingFile")
          );

          let geojsonData;
          try {
            geojsonData = JSON.parse(fileContent);
          } catch {
            throw new Error(t("areas.invalidGeojson"));
          }

          if (!validatePolygonGeometry(geojsonData)) {
            throw new Error(t("areas.polygonRequired"));
          }
          payload.geojson = geojsonData;
        }

        const url = isEdit
          ? `${baseUrl}/area_of_interest/${area.id}/`
          : `${baseUrl}/area_of_interest/`;
        const method = isEdit ? "PATCH" : "POST";

        const response = await authorizedFetch(url, {
          method,
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          const errorKey = isEdit ? "areas.errorUpdating" : "areas.errorCreating";
          throw new Error(formatApiErrors(errorData, t) || t(errorKey));
        }

        const successKey = isEdit ? "areas.updateSuccess" : "areas.createSuccess";
        onSuccess(t(successKey));
        onClose();
      } catch (err) {
        console.error(`Error ${isEdit ? "updating" : "creating"} area:`, err);
        setError(err.message);
      } finally {
        setSubmitting(false);
      }
    },
    [authorizedFetch, baseUrl, area, formData, geojsonFile, isEdit, onClose, onSuccess, t]
  );

  const idPrefix = isEdit ? "edit" : "create";
  const title = isEdit ? t("areas.editArea") : t("areas.addNewArea");

  return (
    <>
      <div className="modal-backdrop fade show" onClick={onClose}></div>
      <div className="modal fade show d-block" tabIndex="-1" role="dialog">
        <div className="modal-dialog modal-dialog-centered" role="document">
          <div className="modal-content">
            <div className="modal-header">
              <h5 className="modal-title">{title}</h5>
              <button
                type="button"
                className="btn-close"
                onClick={onClose}
                aria-label={t("common.close")}
              ></button>
            </div>
            <form onSubmit={handleSubmit}>
              <div className="modal-body">
                {error && (
                  <div className="alert alert-danger" role="alert">
                    <div style={{ whiteSpace: "pre-wrap" }}>{error}</div>
                  </div>
                )}
                <div className="mb-3">
                  <label htmlFor={`${idPrefix}AreaName`} className="form-label">
                    {t("areas.name")} *
                  </label>
                  <input
                    type="text"
                    className="form-control"
                    id={`${idPrefix}AreaName`}
                    name="name"
                    value={formData.name}
                    onChange={handleInputChange}
                    placeholder={t("areas.namePlaceholder")}
                    required
                  />
                </div>

                <div className="mb-3">
                  <label htmlFor={`${idPrefix}AreaCountry`} className="form-label">
                    {t("areas.country")} {!isEdit && "*"}
                  </label>
                  <select
                    className="form-select"
                    id={`${idPrefix}AreaCountry`}
                    name="country"
                    value={formData.country}
                    onChange={handleInputChange}
                    {...(!isEdit ? { required: true } : {})}
                  >
                    <option value="">
                      {isEdit ? t("areas.keepCurrent") : t("areas.selectCountry")}
                    </option>
                    {authorizedCountries.map((country) => (
                      <option key={country.id} value={country.id}>
                        {country.name} ({country.code})
                      </option>
                    ))}
                  </select>
                  {!isEdit && authorizedCountries.length === 0 && (
                    <div className="form-text text-warning">
                      {t("areas.noCountries")}
                    </div>
                  )}
                </div>

                <div className="mb-3">
                  <label htmlFor={`${idPrefix}AreaGeojson`} className="form-label">
                    {t("areas.geojsonFile")} {!isEdit && "*"}
                  </label>
                  <input
                    type="file"
                    className="form-control"
                    id={`${idPrefix}AreaGeojson`}
                    ref={fileInputRef}
                    accept=".geojson,.json"
                    onChange={handleFileChange}
                    {...(!isEdit ? { required: true } : {})}
                  />
                  <div className="form-text">
                    {isEdit ? t("areas.geojsonOptionalHint") : t("areas.geojsonHint")}
                  </div>
                </div>
              </div>
              <div className="modal-footer">
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={onClose}
                  disabled={submitting}
                >
                  {t("areas.cancel")}
                </button>
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
                      {isEdit ? t("areas.saving") : t("areas.creating")}
                    </>
                  ) : isEdit ? (
                    t("areas.save")
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
  );
}

export default AreaFormModal;
