import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useAuth0 } from "@auth0/auth0-react";
import { faro } from "./config/faroConfig";
import { posthog } from "./config/posthogConfig";
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
import { UI_VERSION, APP_ENVIRONMENT } from "./constants/config";

function App() {
  const { t, language, setLanguage } = useLanguage();
  const authAudience = process.env.REACT_APP_AUTH0_AUDIENCE || "";
  const {
    isAuthenticated,
    isLoading: authLoading,
    loginWithRedirect,
    logout,
    user,
    getAccessTokenSilently,
    error: authError,
  } = useAuth0();

  const baseUrl = useMemo(() => {
    const url = process.env.REACT_APP_WILDLIFE_API_URL;
    if (!url) return "";
    return url.endsWith("/") ? url.slice(0, -1) : url;
  }, []);
  const logoSrc = useMemo(() => `${process.env.PUBLIC_URL}/logo.png`, []);
  const authReady = !authLoading && isAuthenticated;

  // Sidebar UI state
  const [isNavOpen, setIsNavOpen] = useState(false);
  const [isSidebarPinned, setIsSidebarPinned] = useState(false);
  const [sidebarCollapsing, setSidebarCollapsing] = useState(false);
  const [showLandingPage, setShowLandingPageState] = useState(() => {
    // Skip landing page when returning from Auth0 callback
    const params = new URLSearchParams(window.location.search);
    if (params.has("code") && params.has("state")) {
      return false;
    }
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

  const login = useCallback(() => {
    const theme = document.documentElement.getAttribute("data-theme") || "dark";
    loginWithRedirect({
      authorizationParams: { ui_locales: language, color_scheme: theme },
    });
  }, [loginWithRedirect, language]);

  const authorizedFetch = useCallback(
    async (url, options = {}) => {
      let token;
      try {
        token = await getAccessTokenSilently({
          authorizationParams: { audience: authAudience },
        });
      } catch (error) {
        const message =
          error?.error_description || error?.message || "Unknown auth error";
        const isExpiredSession =
          error?.error === "login_required" ||
          error?.error === "invalid_grant" ||
          /missing refresh token/i.test(message);
        if (isExpiredSession) {
          console.warn("Session expired, redirecting to login:", message);
          logout({ logoutParams: { returnTo: window.location.origin } });
          return new Promise(() => {}); // never resolves — page will redirect
        }
        console.error("Failed to retrieve access token:", message);
        throw error;
      }

      const headers = { ...(options.headers || {}) };
      if (token) headers.Authorization = `Bearer ${token}`;
      return fetch(url, { ...options, headers });
    },
    [authAudience, getAccessTokenSilently, logout]
  );

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
    markReadByRun,
    fetchUnreadCount,
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

  // Set Faro user metadata for observability correlation
  useEffect(() => {
    if (!faro || !authReady || !user) return;
    faro.api.setUser({
      id: user.sub || "",
      email: user.email || "",
      username: user.name || user.nickname || "",
    });
  }, [authReady, user]);

  // Identify user in PostHog for analytics
  useEffect(() => {
    if (!posthog || !authReady || !user) return;
    posthog.register({ environment: APP_ENVIRONMENT });
    posthog.identify(user.sub, {
      email: user.email,
      name: user.name || user.nickname,
      environment: APP_ENVIRONMENT,
    });
  }, [authReady, user]);

  // Prefer backend profile name, fallback to Auth0 name
  const displayName = useMemo(() => {
    const firstName = backendProfile?.first_name?.trim();
    const lastName = backendProfile?.last_name?.trim();
    if (firstName || lastName) {
      return [firstName, lastName].filter(Boolean).join(" ");
    }
    return user?.name || user?.email || "User";
  }, [backendProfile, user]);

  if (authError) {
    return (
      <div className="app-root d-flex align-items-center justify-content-center min-vh-100">
        <div className="alert alert-danger m-4" role="alert">
          {authError.message || t("app.authFailed")}
          <div className="mt-3">
            <button type="button" className="btn btn-primary" onClick={login}>
              {t("common.tryAgain")}
            </button>
          </div>
        </div>
      </div>
    );
  }

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
    return <div className="page-fade-in"><LandingPage onLogin={login} /></div>;
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
            onClick={() => logout({ logoutParams: { returnTo: window.location.origin } })}
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
        onLogout={() => logout({ logoutParams: { returnTo: window.location.origin } })}
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
                  onNotificationsRead={() => markReadByRun(selectedAnalysisId)}
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
