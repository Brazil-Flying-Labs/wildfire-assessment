import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import "./App.css";
import Breadcrumbs from "./components/Breadcrumbs";
import AnalysisDetail from "./features/analysis-detail/AnalysisDetail";
import AreasOfInterest from "./features/areas/AreasOfInterest";
import Dashboard from "./features/dashboard/Dashboard";
import LandingPage from "./features/landing/LandingPage";
import TermsPage from "./features/terms/TermsPage";
import UserProfile from "./features/profile/UserProfile";
import AnalysisPage from "./features/analysis/AnalysisPage";
import AppHeader from "./features/navigation/AppHeader";
import Sidebar from "./features/navigation/Sidebar";
import useNavigation from "./features/navigation/useNavigation";
import useNotifications from "./hooks/useNotifications";
import useProfile from "./hooks/useProfile";
import { useLanguage } from "./context/LanguageContext";
import { UI_VERSION } from "./constants/config";
import {
  LoginPage,
  ResetPasswordPage,
  SetPasswordPage,
} from "./features/auth/AuthPages";

function getCookie(name) {
  for (const part of document.cookie.split(";")) {
    const [key, ...rest] = part.trim().split("=");
    if (key === name) return decodeURIComponent(rest.join("="));
  }
  return null;
}

// CSRF token cache for write requests. The csrftoken cookie is only
// readable by the UI when both share a host (direct dev flow); through
// the reverse proxy the API lives on a different subdomain, so we keep
// the token returned by /auth/csrf/ instead.
let csrfTokenCache = null;

function App() {
  const { t, language, setLanguage } = useLanguage();

  // Native session state — the backend /me/ endpoint is the source of truth.
  const [sessionUser, setSessionUser] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [authView, setAuthView] = useState(() => {
    if (window.location.pathname.startsWith("/set-password")) {
      return "set-password";
    }
    if (window.location.pathname.startsWith("/reset-password")) {
      return "reset-password";
    }
    if (window.location.pathname === "/login") return "login";
    return "landing";
  });

  const baseUrl = useMemo(() => {
    const url = process.env.REACT_APP_WILDLIFE_API_URL;
    if (!url) return "";
    return url.endsWith("/") ? url.slice(0, -1) : url;
  }, []);
  const logoSrc = useMemo(() => `${process.env.PUBLIC_URL}/logo.png`, []);
  const authReady = !authLoading && !!sessionUser;

  // Plain fetch with credentials and the CSRF token on unsafe methods.
  const fetchJson = useCallback(
    async (url, options = {}) => {
      const method = (options.method || "GET").toUpperCase();
      const headers = { ...(options.headers || {}) };
      if (!["GET", "HEAD", "OPTIONS"].includes(method)) {
        headers["X-CSRFToken"] = getCookie("csrftoken") || csrfTokenCache || "";
      }
      return fetch(url, { ...options, headers, credentials: "include" });
    },
    []
  );

  // Sidebar UI state
  const [isNavOpen, setIsNavOpen] = useState(false);
  const [isSidebarPinned, setIsSidebarPinned] = useState(false);
  const [sidebarCollapsing, setSidebarCollapsing] = useState(false);
  const [showLandingPage, setShowLandingPageState] = useState(() => {
    // On page refresh, check history state to preserve current page
    const state = window.history.state;
    if (state && state.landing === false) {
      return false;
    }
    // If URL is a known app route, skip landing page (handles hard refresh)
    const knownRoutes = ["/dashboard", "/analysis", "/areas", "/profile", "/analysis-detail"];
    if (knownRoutes.includes(window.location.pathname)) {
      return false;
    }
    return true;
  });
  const [dashboardRefreshKey, setDashboardRefreshKey] = useState(0);
  const dashboardRef = useRef(null);

  const setShowLandingPage = useCallback((value) => {
    setShowLandingPageState(value);
  }, []);

  const toggleNav = useCallback(() => setIsNavOpen((prev) => !prev), []);
  const closeNav = useCallback(() => setIsNavOpen(false), []);
  const toggleSidebarPin = useCallback(() => {
    setIsSidebarPinned((prev) => {
      if (prev) setSidebarCollapsing(true);
      return !prev;
    });
  }, []);

  const authorizedFetch = useCallback(
    async (url, options = {}) => {
      const response = await fetchJson(url, options);
      if (response.status === 401) {
        console.warn("Session expired, returning to the landing page");
        setSessionUser(null);
      }
      return response;
    },
    [fetchJson]
  );

  // Check the session on boot: set the CSRF cookie, then ask /me/.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const csrfResponse = await fetchJson(`${baseUrl}/auth/csrf/`);
        if (csrfResponse.ok) {
          const data = await csrfResponse.json();
          if (data.csrfToken) csrfTokenCache = data.csrfToken;
        }
        const response = await fetchJson(`${baseUrl}/me/`);
        if (cancelled) return;
        if (response.ok) {
          setSessionUser(await response.json());
        }
      } catch (error) {
        console.error("Session check failed:", error);
      } finally {
        if (!cancelled) setAuthLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [baseUrl, fetchJson]);

  const handleLoginSuccess = useCallback(async () => {
    try {
      // Login rotates the CSRF token; refresh the cached value before
      // the first authenticated writes.
      const csrfResponse = await fetchJson(`${baseUrl}/auth/csrf/`);
      if (csrfResponse.ok) {
        const data = await csrfResponse.json();
        if (data.csrfToken) csrfTokenCache = data.csrfToken;
      }
      const response = await fetchJson(`${baseUrl}/me/`);
      if (response.ok) setSessionUser(await response.json());
    } catch (error) {
      console.error("Failed to load the profile after login:", error);
    }
  }, [baseUrl, fetchJson]);

  const logout = useCallback(async () => {
    try {
      await fetchJson(`${baseUrl}/auth/logout/`, { method: "POST" });
    } catch (error) {
      console.warn("Logout request failed:", error);
    } finally {
      setSessionUser(null);
    }
  }, [baseUrl, fetchJson]);

  // Navigation
  const {
    currentPage,
    selectedAnalysisId,
    scrollToDeliverable,
    navigateTo,
    handleAnalysisClick,
    goBack,
  } = useNavigation({
    onNavigateTo: closeNav,
    onPopState: useCallback(() => {
      setShowLandingPageState(false);
      setIsNavOpen(false);
    }, []),
  });

  // Profile & theme
  const { backendProfile, accountStatus, fetchBackendProfile, updateTheme, updateDashboardWidgets, acceptTerms } =
    useProfile(authorizedFetch, baseUrl, authReady, language, setLanguage);

  // Notifications
  const {
    notifications,
    unreadCount,
    loading: notificationsLoading,
    hasMore: notificationsHasMore,
    fetchNotifications,
    fetchMore: fetchMoreNotifications,
    markAllRead: handleMarkAllRead,
    markRead: handleMarkRead,
  } = useNotifications(authorizedFetch, baseUrl, authReady);

  // Keep browser tab title in sync with the active language
  useEffect(() => {
    document.title = t("app.title");
  }, [t]);

  // Restart fade-in animation when navigating back to dashboard
  useEffect(() => {
    const el = dashboardRef.current;
    if (currentPage === "dashboard" && el) {
      el.style.animation = "none";
      void el.offsetHeight; // force reflow
      el.style.animation = "";
    }
  }, [currentPage]);

  // Apply theme — dark on landing page when not logged in
  const isOnLandingPage = !authReady || showLandingPage;
  useEffect(() => {
    if (isOnLandingPage && !backendProfile) {
      document.documentElement.setAttribute("data-theme", "dark");
    } else {
      const theme = backendProfile?.theme || "dark";
      document.documentElement.setAttribute("data-theme", theme);
    }
  }, [backendProfile, isOnLandingPage]);



  // Session user mapped to the shape the app components expect.
  const user = useMemo(() => {
    if (!sessionUser) return null;
    const firstName = sessionUser.first_name || "";
    const lastName = sessionUser.last_name || "";
    return {
      email: sessionUser.email,
      given_name: firstName,
      family_name: lastName,
      name: [firstName, lastName].filter(Boolean).join(" ") || sessionUser.email,
    };
  }, [sessionUser]);

  // Prefer backend profile name, fallback to the session user name
  const displayName = useMemo(() => {
    const firstName = backendProfile?.first_name?.trim();
    const lastName = backendProfile?.last_name?.trim();
    if (firstName || lastName) {
      return [firstName, lastName].filter(Boolean).join(" ");
    }
    return user?.name || user?.email || "User";
  }, [backendProfile, user]);

  if (authLoading) {
    return (
      <div className="app-root d-flex align-items-center justify-content-center min-vh-100">
        <div className="text-center">
          <div className="spinner-border text-primary mb-3" role="status">
            <span className="visually-hidden">{t("common.loading")}</span>
          </div>
        </div>
      </div>
    );
  }

  if (!authReady) {
    if (authView === "set-password") {
      return <SetPasswordPage baseUrl={baseUrl} fetchJson={fetchJson} />;
    }
    if (authView === "reset-password") {
      return (
        <ResetPasswordPage
          baseUrl={baseUrl}
          fetchJson={fetchJson}
          onBackToLanding={() => setAuthView("landing")}
        />
      );
    }
    if (authView === "login") {
      return (
        <LoginPage
          baseUrl={baseUrl}
          fetchJson={fetchJson}
          onLoginSuccess={handleLoginSuccess}
          onBackToLanding={() => setAuthView("landing")}
        />
      );
    }
    return (
      <div className="page-fade-in">
        <LandingPage
          baseUrl={baseUrl}
          fetchJson={fetchJson}
          onLogin={() => setAuthView("login")}
        />
      </div>
    );
  }

  if (showLandingPage) {
    return (
      <div className="page-fade-in">
        <LandingPage
          isAuthenticated
          onLogin={() => {
            setShowLandingPage(false);
            window.history.replaceState(
              { page: "dashboard", analysisId: null, landing: false },
              ""
            );
          }}
        />
      </div>
    );
  }

  if (accountStatus === "pending" || (backendProfile && !backendProfile.authorized_countries?.length)) {
    const messageKey = accountStatus === "pending" ? "app.accountPending" : "app.noCountryAccess";
    return (
      <div className="app-root d-flex align-items-center justify-content-center min-vh-100">
        <div className="text-center p-4">
          <img src={logoSrc} alt="" className="brand-logo mb-4" />
          <h2>{t("app.title")}</h2>
          <p className="text-muted mt-3">{t(messageKey)}</p>
          <button
            type="button"
            className="btn btn-outline-secondary mt-3"
            onClick={logout}
          >
            {t("common.logout")}
          </button>
        </div>
      </div>
    );
  }

  const needsTermsAcceptance = backendProfile && (
    !backendProfile.terms_accepted_at ||
    (backendProfile.terms_last_updated &&
      backendProfile.terms_accepted_at < backendProfile.terms_last_updated)
  );

  if (needsTermsAcceptance) {
    return (
      <TermsPage
        logoSrc={logoSrc}
        onAccept={acceptTerms}
        onLogout={logout}
      />
    );
  }

  return (
    <div className="app-root d-flex flex-column min-vh-100">
      <AppHeader
        toggleNav={toggleNav}
        navigateTo={navigateTo}
        logoSrc={logoSrc}
        user={user}
        displayName={displayName}
        logout={logout}
        notificationBellProps={{
          onNotificationClick: handleAnalysisClick,
          unreadCount,
          notifications,
          onOpen: fetchNotifications,
          loading: notificationsLoading,
          hasMore: notificationsHasMore,
          onLoadMore: fetchMoreNotifications,
          onMarkAllRead: handleMarkAllRead,
          onMarkRead: handleMarkRead,
        }}
        t={t}
      />

      <div className="app-body d-flex flex-grow-1">
        <Sidebar
          isOpen={isNavOpen}
          isPinned={isSidebarPinned}
          isCollapsing={sidebarCollapsing}
          currentPage={currentPage}
          navigateTo={navigateTo}
          onClose={closeNav}
          onTogglePin={toggleSidebarPin}
          onCollapsingEnd={() => setSidebarCollapsing(false)}
          user={user}
          displayName={displayName}
          logout={logout}
          t={t}
        />

        <main className="app-main flex-grow-1 d-flex flex-column">
          <Breadcrumbs currentPage={currentPage} navigateTo={navigateTo} />
          <div
            ref={dashboardRef}
            className="page-fade-in"
            style={{ display: currentPage === "dashboard" ? "block" : "none" }}
          >
            <Dashboard
              authorizedFetch={authorizedFetch}
              baseUrl={baseUrl}
              onAnalysisClick={handleAnalysisClick}
              backendProfile={backendProfile}
              onWidgetsChange={updateDashboardWidgets}
              refreshKey={dashboardRefreshKey}
            />
          </div>
          {currentPage === "dashboard" ? null : (
            <div key={currentPage} className="page-fade-in">
              {currentPage === "analysis-detail" && selectedAnalysisId ? (
                <AnalysisDetail
                  authorizedFetch={authorizedFetch}
                  baseUrl={baseUrl}
                  analysisId={selectedAnalysisId}
                  onBack={goBack}
                  scrollToDeliverable={scrollToDeliverable}
                />
              ) : currentPage === "areas" ? (
                <AreasOfInterest
                  authorizedFetch={authorizedFetch}
                  baseUrl={baseUrl}
                  onBack={goBack}
                />
              ) : currentPage === "profile" ? (
                <UserProfile
                  authorizedFetch={authorizedFetch}
                  baseUrl={baseUrl}
                  user={user}
                  backendProfile={backendProfile}
                  onProfileUpdate={fetchBackendProfile}
                  onThemeChange={updateTheme}
                  onBack={goBack}
                  logout={logout}
                />
              ) : (
                <AnalysisPage
                  authorizedFetch={authorizedFetch}
                  baseUrl={baseUrl}
                  onBack={goBack}
                  onAnalysisComplete={() => setDashboardRefreshKey((k) => k + 1)}
                />
              )}
            </div>
          )}
        </main>
      </div>

      <footer className="app-footer mt-auto py-3 text-center small">
        <div className="container-fluid">
          {t("app.footer", { version: UI_VERSION })}
        </div>
      </footer>
    </div>
  );
}

export default App;
