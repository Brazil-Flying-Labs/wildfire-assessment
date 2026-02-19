import { useCallback, useEffect, useState } from "react";
import { useLanguage } from "./LanguageContext";

function UserProfile({ authorizedFetch, baseUrl, user }) {
  const { t } = useLanguage();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [formData, setFormData] = useState({
    firstName: "",
    lastName: "",
  });

  // Load user data from backend
  useEffect(() => {
    if (!baseUrl) return;

    const loadUserData = async () => {
      try {
        const response = await authorizedFetch(`${baseUrl}/me/`);
        if (response.ok) {
          const data = await response.json();
          setFormData({
            firstName: data.first_name || "",
            lastName: data.last_name || "",
          });
        }
      } catch (err) {
        console.error("Error loading user data:", err);
      } finally {
        setLoading(false);
      }
    };

    loadUserData();
  }, [authorizedFetch, baseUrl]);

  const handleInputChange = useCallback((e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  }, []);

  const handleSubmit = useCallback(
    async (e) => {
      e.preventDefault();
      setSaving(true);
      setError(null);
      setSuccess(null);

      try {
        const response = await authorizedFetch(`${baseUrl}/me/`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            first_name: formData.firstName,
            last_name: formData.lastName,
          }),
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(errorData.detail || t("profile.errorSaving"));
        }

        setSuccess(t("profile.saveSuccess"));
      } catch (err) {
        console.error("Error saving profile:", err);
        setError(err.message);
      } finally {
        setSaving(false);
      }
    },
    [authorizedFetch, baseUrl, formData, t]
  );

  if (loading) {
    return (
      <div className="d-flex justify-content-center align-items-center p-5">
        <div className="spinner-border text-primary" role="status">
          <span className="visually-hidden">{t("common.loading")}</span>
        </div>
      </div>
    );
  }

  return (
    <div className="user-profile p-4">
      <h2 className="h4 mb-4">{t("profile.title")}</h2>

      {success && (
        <div className="alert alert-success alert-dismissible fade show" role="alert">
          {success}
          <button
            type="button"
            className="btn-close"
            onClick={() => setSuccess(null)}
            aria-label={t("common.close")}
          ></button>
        </div>
      )}

      {error && (
        <div className="alert alert-danger alert-dismissible fade show" role="alert">
          {error}
          <button
            type="button"
            className="btn-close"
            onClick={() => setError(null)}
            aria-label={t("common.close")}
          ></button>
        </div>
      )}

      <div className="card shadow-sm" style={{ maxWidth: "500px" }}>
        <div className="card-body">
          <form onSubmit={handleSubmit}>
            <div className="mb-3">
              <label htmlFor="profileEmail" className="form-label">
                {t("profile.email")}
              </label>
              <input
                type="email"
                className="form-control"
                id="profileEmail"
                value={user?.email || ""}
                disabled
                readOnly
              />
              <div className="form-text">{t("profile.emailHint")}</div>
            </div>

            <div className="mb-3">
              <label htmlFor="profileFirstName" className="form-label">
                {t("profile.firstName")}
              </label>
              <input
                type="text"
                className="form-control"
                id="profileFirstName"
                name="firstName"
                value={formData.firstName}
                onChange={handleInputChange}
                placeholder={t("profile.firstNamePlaceholder")}
              />
            </div>

            <div className="mb-3">
              <label htmlFor="profileLastName" className="form-label">
                {t("profile.lastName")}
              </label>
              <input
                type="text"
                className="form-control"
                id="profileLastName"
                name="lastName"
                value={formData.lastName}
                onChange={handleInputChange}
                placeholder={t("profile.lastNamePlaceholder")}
              />
            </div>

            <button
              type="submit"
              className="btn btn-primary"
              disabled={saving}
            >
              {saving ? (
                <>
                  <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                  {t("profile.saving")}
                </>
              ) : (
                t("profile.save")
              )}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}

export default UserProfile;
