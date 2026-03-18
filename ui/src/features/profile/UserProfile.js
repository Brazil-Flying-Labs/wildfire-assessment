import { useCallback, useEffect, useRef, useState } from "react";
import BackButton from "../../components/BackButton";
import { useLanguage, SUPPORTED_LANGUAGES } from "../../context/LanguageContext";
import useCookieConsent from "../../hooks/useCookieConsent";
import DeleteAccountModal from "./DeleteAccountModal";

const LANGUAGE_LABELS = {
  en: "English",
  "pt-BR": "Português (Brasil)",
  fr: "Français",
};

const THEME_LABELS = {
  light: { en: "Light", "pt-BR": "Claro", fr: "Clair" },
  dark: { en: "Dark", "pt-BR": "Escuro", fr: "Sombre" },
};

function UserProfile({ authorizedFetch, baseUrl, user, backendProfile, onProfileUpdate, onThemeChange, onBack, logout }) {
  const { t, language, setLanguage } = useLanguage();
  const { consent, resetConsent } = useCookieConsent();
  const [showDeleteModal, setShowDeleteModal] = useState(false);
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

  const handleDeleteAccount = useCallback(async () => {
    const response = await authorizedFetch(`${baseUrl}/me/`, {
      method: "DELETE",
    });
    if (!response.ok) {
      throw new Error("Delete failed");
    }
    logout({ logoutParams: { returnTo: window.location.origin } });
  }, [authorizedFetch, baseUrl, logout]);

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
      <div className="d-flex align-items-center justify-content-between mb-4 page-header-sticky">
        <h2 className="h4 mb-0">{t("profile.title")}</h2>
        <BackButton onClick={onBack} />
      </div>

      <div className="card shadow-sm">
        <div className="card-body">
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

            <div className="mb-3">
              <label htmlFor="profileLanguage" className="form-label">
                {t("profile.language")}
              </label>
              <select
                className="form-select"
                id="profileLanguage"
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
              >
                {SUPPORTED_LANGUAGES.map((lang) => (
                  <option key={lang} value={lang}>
                    {LANGUAGE_LABELS[lang] || lang}
                  </option>
                ))}
              </select>
              <div className="form-text">{t("profile.languageHint")}</div>
            </div>

            <div className="mb-3">
              <label htmlFor="profileTheme" className="form-label">
                {t("profile.theme")}
              </label>
              <select
                className="form-select"
                id="profileTheme"
                value={backendProfile?.theme || "light"}
                onChange={(e) => onThemeChange(e.target.value)}
              >
                <option value="light">{THEME_LABELS.light[language] || "Light"}</option>
                <option value="dark">{THEME_LABELS.dark[language] || "Dark"}</option>
              </select>
              <div className="form-text">{t("profile.themeHint")}</div>
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

      <div className="card shadow-sm mt-4">
        <div className="card-body">
          <h5 className="card-title mb-3">{t("profile.cookieSettings")}</h5>
          <div className={`mb-3 ${consent === "accepted" ? "text-success" : "text-danger"}`}>
            {consent === "accepted" ? t("profile.cookieConsenting") : t("profile.cookieNotConsenting")}
          </div>
          <button
            type="button"
            className="btn btn-outline-secondary btn-sm"
            onClick={resetConsent}
          >
            {consent === "accepted" ? t("profile.revokeCookieConsent") : t("profile.manageCookiePreferences")}
          </button>
          <div className="form-text mt-2">{t("profile.cookieSettingsHint")}</div>
        </div>
      </div>

      <div className="card shadow-sm mt-4">
        <div className="card-body">
          <h5 className="card-title text-danger mb-3">
            {t("profile.deleteAccount")}
          </h5>
          <p className="text-muted mb-3">{t("profile.deleteAccountWarning")}</p>
          <button
            type="button"
            className="btn btn-outline-danger"
            onClick={() => setShowDeleteModal(true)}
          >
            {t("profile.deleteAccount")}
          </button>
        </div>
      </div>

      {showDeleteModal && (
        <DeleteAccountModal
          onConfirm={handleDeleteAccount}
          onClose={() => setShowDeleteModal(false)}
        />
      )}
    </div>
  );
}

export default UserProfile;
