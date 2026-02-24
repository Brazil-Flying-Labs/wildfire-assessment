import { useCallback, useEffect, useRef, useState } from "react";

export default function useProfile(authorizedFetch, baseUrl, authReady, language, setLanguage) {
  const [backendProfile, setBackendProfile] = useState(null);
  const languageLoadedRef = useRef(false);

  const fetchBackendProfile = useCallback(async () => {
    if (!baseUrl) return null;
    try {
      const response = await authorizedFetch(`${baseUrl}/me/`);
      if (response.ok) {
        const data = await response.json();
        setBackendProfile(data);
        return data;
      }
    } catch (error) {
      console.error("Failed to fetch user profile:", error);
    }
    return null;
  }, [authorizedFetch, baseUrl]);

  const updateTheme = useCallback(async (newTheme) => {
    if (!baseUrl) return;
    // Optimistic update - apply theme immediately
    setBackendProfile((prev) => prev ? { ...prev, theme: newTheme } : prev);
    document.documentElement.setAttribute("data-theme", newTheme);
    try {
      await authorizedFetch(`${baseUrl}/me/`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ theme: newTheme }),
      });
    } catch (error) {
      console.error("Failed to update theme:", error);
      // Revert on error
      await fetchBackendProfile();
    }
  }, [authorizedFetch, baseUrl, fetchBackendProfile]);

  const updateDashboardWidgets = useCallback((widgetIds) => {
    if (!baseUrl) return;
    authorizedFetch(`${baseUrl}/me/`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ dashboard_widgets: widgetIds }),
    }).catch((error) => {
      console.error("Failed to update dashboard widgets:", error);
    });
  }, [authorizedFetch, baseUrl]);

  // On login, sync language FROM backend (backend is source of truth)
  useEffect(() => {
    if (!authReady || !baseUrl) return;

    (async () => {
      try {
        const data = await fetchBackendProfile();
        if (data?.default_language && data.default_language !== language) {
          setLanguage(data.default_language);
        }
      } finally {
        languageLoadedRef.current = true;
      }
    })();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authReady, baseUrl]);

  // Persist language changes to backend (only after initial sync from backend)
  useEffect(() => {
    if (!authReady || !baseUrl || !languageLoadedRef.current) return;

    authorizedFetch(`${baseUrl}/me/`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ default_language: language }),
    }).catch((error) => {
      console.error("Failed to update language preference:", error);
    });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [language]);

  return { backendProfile, fetchBackendProfile, updateTheme, updateDashboardWidgets };
}
