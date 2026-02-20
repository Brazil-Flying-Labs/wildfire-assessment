import { useCallback, useEffect, useRef, useState } from "react";
import { useLanguage } from "./LanguageContext";

function UserProfile({ authorizedFetch, baseUrl, user, backendProfile, onProfileUpdate }) {
  const { t } = useLanguage();
  const [loading, setLoading] = useState(!backendProfile);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [formData, setFormData] = useState({
    firstName: "",
    lastName: "",
  });
  const initializedRef = useRef(false);

  // Get Auth0 name parts for prefill fallback
  const getAuth0NameParts = useCallback(() => {
    // Try given_name/family_name first (from Auth0 profile)
    if (user?.given_name || user?.family_name) {
      return {
        firstName: user.given_name || "",
        lastName: user.family_name || "",
      };
    }
    // Fall back to splitting the name field
    if (user?.name) {
      const parts = user.name.trim().split(/\s+/);
      if (parts.length >= 2) {
        return {
          firstName: parts[0],
          lastName: parts.slice(1).join(" "),
        };
      }
      return { firstName: user.name, lastName: "" };
    }
    return { firstName: "", lastName: "" };
  }, [user]);

  // Initialize form data from backend profile (only on first load)
  useEffect(() => {
    if (backendProfile && !initializedRef.current) {
      initializedRef.current = true;
      const backendFirstName = backendProfile.first_name || "";
      const backendLastName = backendProfile.last_name || "";
      
      // If backend has no name, prefill with Auth0 name
      if (!backendFirstName && !backendLastName) {
        const auth0Names = getAuth0NameParts();
        setFormData({
          firstName: auth0Names.firstName,
          lastName: auth0Names.lastName,
        });
      } else {
        setFormData({
          firstName: backendFirstName,
          lastName: backendLastName,
        });
      }
      setLoading(false);
    }
  }, [backendProfile, getAuth0NameParts]);

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

        // Refresh backend profile in parent to update avatar display
        if (onProfileUpdate) {
          await onProfileUpdate();
        }

        setSuccess(t("profile.saveSuccess"));
      } catch (err) {
        console.error("Error saving profile:", err);
        setError(err.message);
      } finally {
        setSaving(false);
      }
    },
    [authorizedFetch, baseUrl, formData, onProfileUpdate, t]
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
