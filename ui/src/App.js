import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useAuth0 } from "@auth0/auth0-react";
import { faro } from "./faroConfig";
import "./App.css";
import AIAnalysisModal from "./AIAnalysisModal";
import AnalysisDetail from "./AnalysisDetail";
import DateRangePicker from "./DateRangePicker";
import LandingPage from "./LandingPage";
import { useLanguage } from "./LanguageContext";
import LanguageSelector from "./LanguageSelector";
import AreasOfInterest from "./AreasOfInterest";
import Dashboard from "./Dashboard";
import NotificationBell from "./NotificationBell";
import UserProfile from "./UserProfile";

const UI_VERSION = "1.4.8";

function App() {
  const { t, language, setLanguage } = useLanguage();
  const languageLoadedRef = useRef(false);
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
  const [areasOfInterest, setAreasOfInterest] = useState([]);
  const [fetchState, setFetchState] = useState({ loading: true, error: null });
  const [selectedReserve, setSelectedReserve] = useState("");
  const [preFireInput, setPreFireInput] = useState("");
  const [postFireInput, setPostFireInput] = useState("");
  const [analysisResult, setAnalysisResult] = useState(null);
  const [analysisState, setAnalysisState] = useState({
    loading: false,
    error: null,
  });
  const [analysisStep, setAnalysisStep] = useState(0);
  const analysisStepRef = useRef(null);
  const [hasResults, setHasResults] = useState(false);
  const [deliverableStatus, setDeliverableStatus] = useState({});
  const [isNavOpen, setIsNavOpen] = useState(false);
  const [isSidebarPinned, setIsSidebarPinned] = useState(false);
  const [sidebarCollapsing, setSidebarCollapsing] = useState(false);
  const [backendProfile, setBackendProfile] = useState(null);
  const [showLandingPage, setShowLandingPageState] = useState(true);
  const setShowLandingPage = useCallback((value) => {
    setShowLandingPageState(value);
  }, []);

  // Page navigation state: "home", "analysis", "areas", or "analysis-detail"
  const [currentPage, setCurrentPage] = useState("dashboard");
  const [selectedAnalysisId, setSelectedAnalysisId] = useState(null);
  const [scrollToDeliverable, setScrollToDeliverable] = useState(null);
  const [dashboardRefreshKey, setDashboardRefreshKey] = useState(0);

  // Notification state
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [notificationsLoading, setNotificationsLoading] = useState(false);
  const [notificationsNextUrl, setNotificationsNextUrl] = useState(null);
  const notificationPollRef = useRef(null);
  const dashboardRef = useRef(null);

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

  const toggleNav = useCallback(() => {
    setIsNavOpen((previous) => !previous);
  }, []);

  const closeNav = useCallback(() => {
    setIsNavOpen(false);
  }, []);

  const toggleSidebarPin = useCallback(() => {
    setIsSidebarPinned((prev) => {
      if (prev) setSidebarCollapsing(true);
      return !prev;
    });
  }, []);

  const navigateTo = useCallback((page, { replace = false } = {}) => {
    setCurrentPage(page);
    setSelectedAnalysisId(null);
    setIsNavOpen(false);
    const state = { page, analysisId: null, landing: false };
    if (replace) {
      window.history.replaceState(state, "");
    } else {
      window.history.pushState(state, "");
    }
    if (faro) faro.api.setView({ name: page });
  }, []);

  const handleAnalysisClick = useCallback((analysisId, deliverableName) => {
    setSelectedAnalysisId(analysisId);
    setScrollToDeliverable(deliverableName || null);
    setCurrentPage("analysis-detail");
    window.history.pushState(
      { page: "analysis-detail", analysisId, landing: false },
      ""
    );
    if (faro) faro.api.setView({ name: "analysis-detail" });
  }, []);

  const handleBackFromAnalysisDetail = useCallback(() => {
    setSelectedAnalysisId(null);
    setCurrentPage("dashboard");
    window.history.pushState(
      { page: "dashboard", analysisId: null, landing: false },
      ""
    );
    if (faro) faro.api.setView({ name: "dashboard" });
  }, []);

  // Handle browser back/forward buttons
  useEffect(() => {
    const handlePopState = (event) => {
      const state = event.state;
      if (!state) {
        // No state — push current page into history to prevent leaving the app
        window.history.pushState(
          { page: "dashboard", analysisId: null, landing: false },
          ""
        );
        return;
      }
      setShowLandingPageState(false);
      setCurrentPage(state.page || "dashboard");
      setSelectedAnalysisId(state.analysisId || null);
      setIsNavOpen(false);
      if (faro) faro.api.setView({ name: state.page || "dashboard" });
    };

    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  const [backendAuthorizationError, setBackendAuthorizationError] = useState(false);
  const logoSrc = useMemo(() => `${process.env.PUBLIC_URL}/logo.png`, []);
  const baseUrl = useMemo(() => {
    const url = process.env.REACT_APP_WILDLIFE_API_URL;

    if (!url) {
      return "";
    }

    return url.endsWith("/") ? url.slice(0, -1) : url;
  }, []);
  const analyzeControllerRef = useRef(null);
  const deliverablePollRef = useRef({});

  const authReady = !authLoading && isAuthenticated;


  const login = useCallback(
    () => {
      const theme = document.documentElement.getAttribute("data-theme") || "dark";
      loginWithRedirect({
        authorizationParams: {
          ui_locales: language,
          color_scheme: theme,
        },
      });
    },
    [loginWithRedirect, language]
  );

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
        console.error("Failed to retrieve access token:", message);
        if (
          error?.error === "login_required" ||
          error?.error === "invalid_grant" ||
          /missing refresh token/i.test(message)
        ) {
          logout({ logoutParams: { returnTo: window.location.origin } });
        }
        throw error;
      }

      const headers = {
        ...(options.headers || {}),
      };

      if (token) {
        headers.Authorization = `Bearer ${token}`;
      }

      return fetch(url, {
        ...options,
        headers,
      });
    },
    [authAudience, getAccessTokenSilently, logout]
  );

  const ensureAuthorizedResponse = useCallback(
    (response) => {
      if (response?.status === 403) {
        setBackendAuthorizationError(true);
        throw new Error(t("app.backendUnauthorized"));
      }
      return response;
    },
    [setBackendAuthorizationError, t]
  );

  // Fetch backend profile and sync language on login.
  const fetchBackendProfile = useCallback(async () => {
    if (!baseUrl) return;
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

  // Notification sound
  const prevUnreadRef = useRef(null);
  const playNotificationSound = useCallback(() => {
    try {
      const ctx = new (window.AudioContext || window.webkitAudioContext)();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.type = "sine";
      // Two-tone chime
      osc.frequency.setValueAtTime(880, ctx.currentTime);
      osc.frequency.setValueAtTime(1174.66, ctx.currentTime + 0.1);
      gain.gain.setValueAtTime(0.3, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.3);
      osc.start(ctx.currentTime);
      osc.stop(ctx.currentTime + 0.3);
    } catch {
      // Audio not available — ignore
    }
  }, []);

  // Notification polling
  const fetchUnreadCount = useCallback(async () => {
    if (!baseUrl) return;
    try {
      const response = await authorizedFetch(
        `${baseUrl}/notifications/unread_count/`
      );
      if (response.ok) {
        const data = await response.json();
        const newCount = data.unread_count;
        if (prevUnreadRef.current !== null && newCount > prevUnreadRef.current) {
          playNotificationSound();
        }
        prevUnreadRef.current = newCount;
        setUnreadCount(newCount);
      }
    } catch {
      // Silently ignore polling errors
    }
  }, [authorizedFetch, baseUrl, playNotificationSound]);

  const fetchNotifications = useCallback(
    async (nextUrl) => {
      if (!baseUrl) return;
      const url = nextUrl || `${baseUrl}/notifications/`;
      setNotificationsLoading(true);
      try {
        const response = await authorizedFetch(url);
        if (response.ok) {
          const data = await response.json();
          setNotifications((prev) =>
            nextUrl ? [...prev, ...(data.results || [])] : data.results || []
          );
          setNotificationsNextUrl(data.next);
        }
      } catch {
        // Silently ignore
      } finally {
        setNotificationsLoading(false);
      }
    },
    [authorizedFetch, baseUrl]
  );

  const fetchMoreNotifications = useCallback(() => {
    if (notificationsNextUrl && !notificationsLoading) {
      fetchNotifications(notificationsNextUrl);
    }
  }, [notificationsNextUrl, notificationsLoading, fetchNotifications]);

  const handleMarkAllRead = useCallback(async () => {
    if (!baseUrl) return;
    try {
      const response = await authorizedFetch(
        `${baseUrl}/notifications/mark-all-read/`,
        { method: "POST" }
      );
      if (response.ok) {
        setNotifications((prev) =>
          prev.map((n) => ({ ...n, is_read: true }))
        );
        setUnreadCount(0);
        prevUnreadRef.current = 0;
      }
    } catch {
      // Silently ignore
    }
  }, [authorizedFetch, baseUrl]);

  // Apply theme to document — dark on landing page when not logged in
  const isOnLandingPage = !authReady || showLandingPage;
  useEffect(() => {
    if (isOnLandingPage && !backendProfile) {
      document.documentElement.setAttribute("data-theme", "dark");
    } else {
      const theme = backendProfile?.theme || "dark";
      document.documentElement.setAttribute("data-theme", theme);
    }
  }, [backendProfile, isOnLandingPage]);

  // Update theme preference
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

  // Update dashboard widget layout preference
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

  // Set Faro user metadata for observability correlation
  useEffect(() => {
    if (!faro || !authReady || !user) return;
    faro.api.setUser({
      id: user.sub || "",
      email: user.email || "",
      username: user.name || user.nickname || "",
    });
  }, [authReady, user]);

  // Poll for unread notification count every 5 seconds
  useEffect(() => {
    if (!authReady || !baseUrl) return;
    fetchUnreadCount();
    notificationPollRef.current = setInterval(fetchUnreadCount, 5000);
    return () => {
      if (notificationPollRef.current) clearInterval(notificationPollRef.current);
    };
  }, [authReady, baseUrl, fetchUnreadCount]);

  const loadReserves = useCallback(() => {
    if (!baseUrl) {
      setFetchState({
        loading: false,
        error: t("app.envNotConfigured"),
      });
      return undefined;
    }

    const controller = new AbortController();

    setFetchState({ loading: true, error: null });

    (async () => {
      try {
        const response = await authorizedFetch(
          `${baseUrl}/area_of_interest/?page_size=999999999`,
          {
            signal: controller.signal,
          }
        );

        ensureAuthorizedResponse(response);

        if (!response.ok) {
          throw new Error(t("app.errorLoadingReserves", { status: response.status }));
        }

        const data = await response.json();
        // Handle both paginated and non-paginated responses
        setAreasOfInterest(data.results || data);
        setFetchState({ loading: false, error: null });
      } catch (error) {
        if (error.name === "AbortError") return;

        console.error("Failed to fetch ecological reserves:", error);
        setFetchState({ loading: false, error: error.message });
      }
    })();

    return () => controller.abort();
  }, [authorizedFetch, baseUrl, ensureAuthorizedResponse, t]);

  useEffect(() => {
    if (!authReady) {
      return undefined;
    }

    const abort = loadReserves();
    return () => {
      if (typeof abort === "function") {
        abort();
      }
    };
  }, [authReady, loadReserves]);

  useEffect(() => {
    return () => {
      if (analyzeControllerRef.current) {
        analyzeControllerRef.current.abort();
      }
    };
  }, []);

  const hasError = Boolean(fetchState.error);

  const normalizeDateValue = useCallback((rawValue) => {
    if (!rawValue) {
      return "";
    }

    const trimmed = rawValue.trim();
    if (!trimmed) {
      return "";
    }

    if (/^\d{4}-\d{2}-\d{2}$/.test(trimmed)) {
      return trimmed;
    }

    const parsed = new Date(trimmed);
    if (Number.isNaN(parsed.getTime())) {
      return "";
    }

    return parsed.toISOString().slice(0, 10);
  }, []);

  const isIsoDate = useCallback(
    (value) => /^\d{4}-\d{2}-\d{2}$/.test(value || ""),
    []
  );

  const preFireDate = useMemo(
    () => (isIsoDate(preFireInput) ? preFireInput : ""),
    [preFireInput, isIsoDate]
  );

  const postFireDate = useMemo(
    () => (isIsoDate(postFireInput) ? postFireInput : ""),
    [postFireInput, isIsoDate]
  );

  const renderReserveOptions = () => {
    if (fetchState.loading) {
      return (
        <option value="" disabled>
          {t("app.loadingReserves")}
        </option>
      );
    }

    if (hasError) {
      return (
        <option value="" disabled>
          {fetchState.error}
        </option>
      );
    }

    if (!areasOfInterest.length) {
      return (
        <option value="" disabled>
          {t("app.noReserves")}
        </option>
      );
    }

    return [
      <option key="placeholder" value="" disabled>
        {t("app.chooseOption")}
      </option>,
      ...areasOfInterest.map((reserve) => (
        <option key={reserve.id} value={reserve.id}>
          {reserve.name}
        </option>
      )),
    ];
  };

  const isAnalyzeDisabled =
    fetchState.loading ||
    hasError ||
    analysisState.loading ||
    !selectedReserve ||
    !preFireDate ||
    !postFireDate;

  const formatLabel = useCallback((key) => {
    const withoutSuffix = key.replace(/_(jpg|tif)$/i, "");
    return withoutSuffix
      .split("_")
      .map((word) => {
        if (word.length <= 3) return word.toUpperCase();
        return word.charAt(0).toUpperCase() + word.slice(1);
      })
      .join(" ");
  }, []);

  const imageEntries = useMemo(() => {
    if (!analysisResult) return [];
    return Object.entries(analysisResult).filter(
      ([key, value]) => key.endsWith("_jpg") && typeof value === "string"
    );
  }, [analysisResult]);

  const tiffEntries = useMemo(() => {
    if (!analysisResult) return [];
    return Object.entries(analysisResult).filter(
      ([key, value]) => key.endsWith("_tif") && typeof value === "string"
    );
  }, [analysisResult]);

  const csvEntry = useMemo(() => {
    if (!analysisResult) return null;
    const entry = Object.entries(analysisResult).find(
      ([key, value]) => key.endsWith("_stats") && typeof value === "string"
    );
    return entry || null;
  }, [analysisResult]);

  const parseLocaleNumber = useCallback((rawValue) => {
    if (rawValue === null || rawValue === undefined) return Number.NaN;
    if (typeof rawValue === "number") return rawValue;
    if (typeof rawValue !== "string") return Number.NaN;

    const trimmed = rawValue.trim();
    if (!trimmed) return Number.NaN;

    const sanitized = trimmed
      .replace(/%$/g, "")
      .replace(/ha$/gi, "")
      .trim();

    if (!sanitized) return Number.NaN;

    let normalized = sanitized;

    if (sanitized.includes(",") && sanitized.includes(".")) {
      normalized = sanitized.replace(/\./g, "").replace(",", ".");
    } else if (sanitized.includes(",")) {
      normalized = sanitized.replace(",", ".");
    }

    const numeric = Number(normalized);

    if (Number.isNaN(numeric)) {
      return Number.NaN;
    }

    return numeric;
  }, []);

  const formatAreaValue = useCallback(
    (value) => {
      if (value === null || value === undefined || value === "") return "";

      const numericValue = parseLocaleNumber(value);

      if (Number.isNaN(numericValue)) {
        return typeof value === "string" ? value : `${value}`;
      }

      const formatted = numericValue.toLocaleString("pt-BR", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      });

      return `${formatted} ha`;
    },
    [parseLocaleNumber]
  );

  const formatPercentValue = useCallback(
    (value) => {
      if (value === null || value === undefined || value === "") return "";

      const numericValue = parseLocaleNumber(value);

      if (Number.isNaN(numericValue)) {
        return typeof value === "string" ? value : `${value}`;
      }

      const formatted = numericValue.toLocaleString("pt-BR", {
        minimumFractionDigits: 3,
        maximumFractionDigits: 3,
      });

      return `${formatted}%`;
    },
    [parseLocaleNumber]
  );


  const bestDates = useMemo(() => {
    if (!analysisResult) return null;
    const { pre_fire_best_date: preBest, post_fire_best_date: postBest } =
      analysisResult;
    const formattedPre = normalizeDateValue(preBest);
    const formattedPost = normalizeDateValue(postBest);
    if (!formattedPre && !formattedPost) return null;
    return { preBest: formattedPre, postBest: formattedPost };
  }, [analysisResult, normalizeDateValue]);

  const severityEntries = useMemo(() => {
    const mapData = analysisResult?.severity_map;
    if (!mapData) return [];

    try {
      const parsed =
        typeof mapData === "string" ? JSON.parse(mapData) : mapData || {};
      const entries = Object.entries(parsed).map(([name, metrics]) => ({
        name,
        area: metrics?.area_ha ?? metrics?.area ?? null,
        percent: metrics?.ratio_percent ?? metrics?.percent ?? null,
      }));

      const severityOrder = [
        "Unburned",
        "Low Severity",
        "Moderate Severity",
        "High Severity",
        "Very High Severity",
        "Total Burned Area",
        "Total Area",
      ];

      entries.sort((a, b) => {
        const orderA = severityOrder.indexOf(a.name);
        const orderB = severityOrder.indexOf(b.name);
        if (orderA === -1 && orderB === -1) {
          return a.name.localeCompare(b.name);
        }
        if (orderA === -1) return 1;
        if (orderB === -1) return -1;
        return orderA - orderB;
      });

      return entries;
    } catch (error) {
      console.error("Failed to parse severity map:", error);
      return [];
    }
  }, [analysisResult]);

  const severityColorMap = useMemo(
    () => ({
      "Unburned": "#28a745",
      "Low Severity": "#ffc107",
      "Moderate Severity": "#fd7e14",
      "High Severity": "#dc3545",
      "Very High Severity": "#6f42c1"
    }),
    []
  );

  const severityTranslationMap = useMemo(
    () => ({
      "Unburned": t("severity.unburned"),
      "Low Severity": t("severity.low"),
      "Moderate Severity": t("severity.moderate"),
      "High Severity": t("severity.high"),
      "Very High Severity": t("severity.veryHigh"),
      "Total Burned Area": t("severity.totalBurned"),
      "Total Area": t("severity.totalArea"),
    }),
    [t]
  );

  const handleDownloadSeverityCsv = useCallback(() => {
    if (!severityEntries.length) return;
    const header = "Severity,Area (ha),Percent\n";
    const rows = severityEntries
      .map(({ name, area, percent }) => {
        const areaVal = area !== null && area !== undefined ? area : "";
        const pctVal = percent !== null && percent !== undefined ? percent : "";
        return `"${name}",${areaVal},${pctVal}`;
      })
      .join("\n");
    const blob = new Blob([header + rows], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "severity_distribution.csv";
    link.click();
    URL.revokeObjectURL(url);
  }, [severityEntries]);

  const scientificDeliverables = useMemo(
    () => [
      { label: "RGB pre-fire", value: "RGB_PRE_FIRE", urlKey: "scientific_rgb_pre_fire_url", taskKey: "scientific_rgb_pre_fire_task_id" },
      { label: "RGB post-fire", value: "RGB_POST_FIRE", urlKey: "scientific_rgb_post_fire_url", taskKey: "scientific_rgb_post_fire_task_id" },
      { label: "dNBR", value: "DNBR", urlKey: "scientific_dnbr_url", taskKey: "scientific_dnbr_task_id" },
      { label: "RBR", value: "RBR", urlKey: "scientific_rbr_url", taskKey: "scientific_rbr_task_id" },
      { label: "dNDVI", value: "DNDVI", urlKey: "scientific_dndvi_url", taskKey: "scientific_dndvi_task_id" },
    ],
    []
  );

  const isScientificDeliverableDisabled =
    fetchState.loading || hasError || !selectedReserve || !preFireDate || !postFireDate;

  const updateDeliverableStatus = useCallback((deliverableName, nextState) => {
    setDeliverableStatus((previous) => ({
      ...previous,
      [deliverableName]: {
        ...(previous[deliverableName] || {}),
        ...nextState,
      },
    }));
  }, []);

  const startDeliverablePolling = useCallback(
    (deliverableName, taskId, analysisRunId) => {
      if (deliverablePollRef.current[deliverableName]) {
        clearInterval(deliverablePollRef.current[deliverableName]);
      }

      const intervalId = setInterval(async () => {
        try {
          const params = new URLSearchParams({
            task_id: taskId,
            deliverable: deliverableName,
          });
          const url = `${baseUrl}/analysis_run/${analysisRunId}/task_status/?${params.toString()}`;
          const response = await authorizedFetch(url);
          if (!response.ok) return;

          const data = await response.json();

          if (data.state === "SUCCESS") {
            clearInterval(deliverablePollRef.current[deliverableName]);
            delete deliverablePollRef.current[deliverableName];
            updateDeliverableStatus(deliverableName, {
              polling: false,
              url: data.url || null,
            });
          } else if (data.state === "FAILURE") {
            clearInterval(deliverablePollRef.current[deliverableName]);
            delete deliverablePollRef.current[deliverableName];
            updateDeliverableStatus(deliverableName, {
              polling: false,
              error: data.error || t("app.deliverableError"),
            });
          }
        } catch {
          // Ignore polling errors, will retry on next interval
        }
      }, 5000);

      deliverablePollRef.current[deliverableName] = intervalId;
    },
    [authorizedFetch, baseUrl, updateDeliverableStatus, t]
  );

  // Cleanup polling intervals on unmount
  useEffect(() => {
    const intervals = deliverablePollRef.current;
    return () => {
      Object.values(intervals).forEach(clearInterval);
    };
  }, []);

  const handleScientificDeliverable = useCallback(
    async (deliverableName) => {
      if (isScientificDeliverableDisabled) {
        return;
      }

      updateDeliverableStatus(deliverableName, {
        loading: true,
        error: null,
        url: null,
      });

      try {
        if (!baseUrl) {
          throw new Error(t("app.apiNotConfigured"));
        }

        const queryParams = new URLSearchParams({
          pre_fire_date: preFireDate,
          post_fire_date: postFireDate,
          deliverable: deliverableName,
        });
        if (analysisResult?.analysis_run_id) {
          queryParams.set("analysis_run_id", analysisResult.analysis_run_id);
        }

        const url = `${baseUrl}/area_of_interest/${selectedReserve}/scientific_deliverable/?${queryParams.toString()}`;

        const response = await authorizedFetch(url, { method: "POST" });
        ensureAuthorizedResponse(response);

        if (!response.ok) {
          throw new Error(t("app.errorDeliverable", { status: response.status }));
        }

        const data = await response.json();
        updateDeliverableStatus(deliverableName, {
          loading: false,
          polling: true,
        });
        if (data.task_id && analysisResult?.analysis_run_id) {
          startDeliverablePolling(
            deliverableName,
            data.task_id,
            analysisResult.analysis_run_id
          );
        }
      } catch (error) {
        console.error("Failed to request scientific deliverable:", error);
        updateDeliverableStatus(deliverableName, {
          loading: false,
          error: error.message || "Unknown error",
        });
      }
    },
    [
      analysisResult,
      authorizedFetch,
      baseUrl,
      ensureAuthorizedResponse,
      isScientificDeliverableDisabled,
      preFireDate,
      postFireDate,
      selectedReserve,
      startDeliverablePolling,
      updateDeliverableStatus,
      t,
    ]
  );

  const analysisSteps = useMemo(
    () => [
      t("app.progressStep1"),
      t("app.progressStep2"),
      t("app.progressStep3"),
      t("app.progressStep4"),
      t("app.progressStep5"),
    ],
    [t]
  );

  const handleSubmit = async (event) => {
    event.preventDefault();

    if (isAnalyzeDisabled) {
      return;
    }

    if (!baseUrl) {
      setAnalysisState({
        loading: false,
        error: t("app.apiNotConfigured"),
      });
      return;
    }

    if (analyzeControllerRef.current) {
      analyzeControllerRef.current.abort();
    }

    const controller = new AbortController();
    analyzeControllerRef.current = controller;

    setAnalysisState({ loading: true, error: null });
    setAnalysisResult(null);
    setHasResults(false);
    setAnalysisStep(0);
    clearInterval(analysisStepRef.current);
    analysisStepRef.current = setInterval(() => {
      setAnalysisStep((prev) => (prev < 4 ? prev + 1 : prev));
    }, 6000);
    // Clear polling intervals and deliverable state
    Object.values(deliverablePollRef.current).forEach(clearInterval);
    deliverablePollRef.current = {};
    setDeliverableStatus({});

    try {
      const queryParams = new URLSearchParams({
        pre_fire_date: preFireDate,
        post_fire_date: postFireDate,
      });
      const url = `${baseUrl}/area_of_interest/${selectedReserve}/analyze/?${queryParams.toString()}`;

      const response = await authorizedFetch(url, {
        method: "POST",
        signal: controller.signal,
      });

      ensureAuthorizedResponse(response);

      if (!response.ok) {
        throw new Error(t("app.errorAnalysis", { status: response.status }));
      }

      const data = await response.json();
      setAnalysisResult(data);
      setHasResults(true);
      setAnalysisState({ loading: false, error: null });
      setDashboardRefreshKey((k) => k + 1);
    } catch (error) {
      if (error.name === "AbortError") {
        if (analyzeControllerRef.current === controller) {
          setAnalysisState({ loading: false, error: null });
        }
        return;
      }

      console.error("Error during analysis:", error);
      setAnalysisState({ loading: false, error: error.message });
    } finally {
      clearInterval(analysisStepRef.current);
      setAnalysisStep(0);
      if (analyzeControllerRef.current === controller) {
        analyzeControllerRef.current = null;
      }
    }
  };

  // AI Analysis feature - memoized values for the API call
  const selectedReserveName = useMemo(() => {
    if (!selectedReserve || !areasOfInterest.length) return "";
    const reserve = areasOfInterest.find((r) => String(r.id) === String(selectedReserve));
    return reserve?.name || "";
  }, [selectedReserve, areasOfInterest]);

  const severityDistributionForAPI = useMemo(() => {
    if (!severityEntries.length) return {};
    return severityEntries.reduce((acc, { name, area, percent }) => {
      acc[name] = {
        area_ha: typeof area === "number" ? area : parseFloat(area) || 0,
        percent: typeof percent === "number" ? percent : parseFloat(percent) || 0,
      };
      return acc;
    }, {});
  }, [severityEntries]);

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
            <button
              type="button"
              className="btn btn-primary"
              onClick={login}
            >
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

  return (
    <div className="app-root d-flex flex-column min-vh-100">
      <header className="app-header text-white">
        <div className="container-fluid d-flex align-items-center justify-content-between py-3 gap-3">
          <div className="d-flex align-items-center gap-2 gap-md-3 header-brand">
            {/* Hamburger menu button */}
            <button
              type="button"
              className="btn btn-link text-white p-0 nav-toggle-btn"
              onClick={toggleNav}
              aria-label="Toggle navigation"
            >
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="3" y1="6" x2="21" y2="6" />
                <line x1="3" y1="12" x2="21" y2="12" />
                <line x1="3" y1="18" x2="21" y2="18" />
              </svg>
            </button>
            <button
              type="button"
              className="btn p-0 border-0 bg-transparent header-logo-btn"
              onClick={() => navigateTo("dashboard")}
              aria-label={t("landing.title")}
            >
              <img
                src={logoSrc}
                alt={t("landing.title")}
                className="brand-logo"
              />
            </button>
            <div className="d-none d-md-block">
              <h1 className="h4 mb-0">{t("app.title")}</h1>
            </div>
          </div>

          <div className="d-flex align-items-center gap-2 header-actions">
            <LanguageSelector />
            <NotificationBell
              onNotificationClick={handleAnalysisClick}
              unreadCount={unreadCount}
              notifications={notifications}
              onOpen={fetchNotifications}
              loading={notificationsLoading}
              hasMore={!!notificationsNextUrl}
              onLoadMore={fetchMoreNotifications}
              onMarkAllRead={handleMarkAllRead}
            />
            <div className="avatar-menu">
              {user?.picture ? (
                <img
                  src={user.picture}
                  alt={displayName}
                  title={displayName}
                  className="rounded-circle avatar-trigger"
                  width="32"
                  height="32"
                  referrerPolicy="no-referrer"
                />
              ) : (
                <span className="avatar-fallback rounded-circle avatar-trigger">
                  {displayName.charAt(0).toUpperCase()}
                </span>
              )}
              <div className="avatar-dropdown">
                <div className="avatar-dropdown-inner">
                  <p className="avatar-dropdown-name">{displayName}</p>
                  <button
                    type="button"
                    className="btn btn-outline-light btn-sm w-100"
                    onClick={() =>
                      logout({ logoutParams: { returnTo: window.location.origin } })
                    }
                  >
                    {t("common.logout")}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </header>

      <div className="app-body d-flex flex-grow-1">
        {/* Navigation Sidebar */}
        {isNavOpen && (
          <button
            type="button"
            className="nav-backdrop"
            onClick={closeNav}
            aria-label={t("common.close")}
          >
            <span className="visually-hidden">{t("common.close")}</span>
          </button>
        )}
        <nav
          className={`nav-sidebar ${isSidebarPinned ? "is-pinned" : ""} ${sidebarCollapsing ? "is-collapsing" : ""} ${isNavOpen ? "is-open" : ""}`}
          onMouseLeave={() => sidebarCollapsing && setSidebarCollapsing(false)}
        >
          <div className="nav-sidebar-header d-flex justify-content-end align-items-center p-3">
            <button
              type="button"
              className="btn btn-link text-dark p-0"
              onClick={closeNav}
              aria-label={t("common.close")}
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>
          <ul className="nav-sidebar-menu list-unstyled m-0 p-0">
            <li>
              <button
                type="button"
                className={`nav-sidebar-item ${currentPage === "dashboard" ? "active" : ""}`}
                onClick={() => navigateTo("dashboard")}
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="3" y="3" width="7" height="7" />
                  <rect x="14" y="3" width="7" height="7" />
                  <rect x="14" y="14" width="7" height="7" />
                  <rect x="3" y="14" width="7" height="7" />
                </svg>
                <span>{t("nav.dashboard")}</span>
              </button>
            </li>
            <li>
              <button
                type="button"
                className={`nav-sidebar-item ${currentPage === "analysis" ? "active" : ""}`}
                onClick={() => navigateTo("analysis")}
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
                </svg>
                <span>{t("nav.analysis")}</span>
              </button>
            </li>
            <li>
              <button
                type="button"
                className={`nav-sidebar-item ${currentPage === "areas" ? "active" : ""}`}
                onClick={() => navigateTo("areas")}
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6" />
                  <line x1="8" y1="2" x2="8" y2="18" />
                  <line x1="16" y1="6" x2="16" y2="22" />
                </svg>
                <span>{t("nav.areas")}</span>
              </button>
            </li>
            <li>
              <button
                type="button"
                className={`nav-sidebar-item ${currentPage === "profile" ? "active" : ""}`}
                onClick={() => navigateTo("profile")}
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                  <circle cx="12" cy="7" r="4" />
                </svg>
                <span>{t("nav.profile")}</span>
              </button>
            </li>
          </ul>
          <div className="nav-sidebar-pin">
            <button
              type="button"
              className="nav-sidebar-item"
              onClick={toggleSidebarPin}
              title={isSidebarPinned ? t("nav.collapse") : t("nav.keepOpen")}
            >
              {isSidebarPinned ? (
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="11 17 6 12 11 7" />
                  <polyline points="18 17 13 12 18 7" />
                </svg>
              ) : (
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="6 17 11 12 6 7" />
                  <polyline points="13 17 18 12 13 7" />
                </svg>
              )}
              <span>{isSidebarPinned ? t("nav.collapse") : t("nav.keepOpen")}</span>
            </button>
          </div>
          <div className="nav-sidebar-footer">
            <div className="d-flex align-items-center gap-3 w-100">
              {user?.picture ? (
                <img
                  src={user.picture}
                  alt={displayName}
                  className="rounded-circle flex-shrink-0"
                  width="36"
                  height="36"
                  referrerPolicy="no-referrer"
                />
              ) : (
                <span className="avatar-fallback rounded-circle flex-shrink-0">
                  {displayName.charAt(0).toUpperCase()}
                </span>
              )}
              <div className="min-width-0">
                <div className="fw-medium small text-truncate">{displayName}</div>
                <button
                  type="button"
                  className="btn btn-link btn-sm p-0 text-muted"
                  onClick={() =>
                    logout({ logoutParams: { returnTo: window.location.origin } })
                  }
                >
                  {t("common.logout")}
                </button>
              </div>
            </div>
          </div>
        </nav>

        {/* Main Content */}
        <main className="app-main flex-grow-1 d-flex flex-column">
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
              onBack={handleBackFromAnalysisDetail}
              onNotificationsRead={fetchUnreadCount}
              scrollToDeliverable={scrollToDeliverable}
            />
          ) : currentPage === "areas" ? (
            <AreasOfInterest
              authorizedFetch={authorizedFetch}
              baseUrl={baseUrl}
              onBackToDashboard={handleBackFromAnalysisDetail}
            />
          ) : currentPage === "profile" ? (
            <UserProfile
              authorizedFetch={authorizedFetch}
              baseUrl={baseUrl}
              user={user}
              backendProfile={backendProfile}
              onProfileUpdate={fetchBackendProfile}
              onThemeChange={updateTheme}
              onBackToDashboard={handleBackFromAnalysisDetail}
            />
          ) : !backendAuthorizationError ? (
            <section className="app-main-content p-4 flex-grow-1">
              {backendAuthorizationError ? (
                <div className="alert alert-warning" role="alert">
                  {t("app.backendUnauthorized")}
                </div>
              ) : null}

              <div className="d-flex align-items-center justify-content-between mb-4 page-header-sticky">
                <h2 className="h4 mb-0">{t("app.analysisTitle")}</h2>
                <button
                  type="button"
                  className="btn btn-outline-secondary btn-sm d-flex align-items-center gap-1 no-print"
                  onClick={handleBackFromAnalysisDetail}
                  title={t("common.back")}
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="19" y1="12" x2="5" y2="12" />
                    <polyline points="12 19 5 12 12 5" />
                  </svg>
                  {t("common.back")}
                </button>
              </div>

              {/* Analysis Form Card */}
              <div className="card shadow-sm mb-4 no-print">
                <div className="card-header">
                  <h3 className="h5 mb-0">{t("app.analysisParams")}</h3>
                </div>
                <div className="card-body">
                  <form onSubmit={handleSubmit}>
                    <div className="row g-3">
                      <div className="col-12 col-lg-6">
                        <DateRangePicker
                          startDate={preFireDate}
                          endDate={postFireDate}
                          onRangeChange={(start, end) => {
                            setPreFireInput(start);
                            setPostFireInput(end);
                          }}
                          label={t("app.dateRange")}
                          startLabel={t("app.preFire")}
                          endLabel={t("app.postFire")}
                        />
                      </div>

                      <div className="col-12 col-md-6 col-lg-4">
                        <label htmlFor="reserve" className="form-label">
                          {t("app.selectArea")}
                        </label>
                        <select
                          className="form-select"
                          id="reserve"
                          name="reserve"
                          value={selectedReserve}
                          onChange={(event) => setSelectedReserve(event.target.value)}
                          disabled={fetchState.loading || hasError}
                        >
                          {renderReserveOptions()}
                        </select>
                        {hasError ? (
                          <div className="mt-2">
                            <p className="small text-danger mb-2">
                              {t("app.apiHint")}
                            </p>
                            <button
                              type="button"
                              className="btn btn-outline-danger btn-sm"
                              onClick={loadReserves}
                            >
                              {t("common.tryAgain")}
                            </button>
                          </div>
                        ) : null}
                      </div>

                      <div className="col-12 col-md-6 col-lg-2 d-flex align-items-end">
                        <button
                          type="submit"
                          className="btn btn-primary w-100"
                          disabled={isAnalyzeDisabled}
                        >
                          {analysisState.loading ? t("app.analyzing") : t("app.runAnalysis")}
                        </button>
                      </div>
                    </div>
                  </form>
                </div>
              </div>

              {/* Analysis Results */}
              {analysisState.loading ? (
                <div className="card shadow-sm">
                  <div className="card-body p-4">
                    <div className="analysis-progress-bar mb-4">
                      <div
                        className="analysis-progress-bar__fill"
                        style={{ width: `${((analysisStep + 1) / analysisSteps.length) * 100}%` }}
                      />
                    </div>
                    <div className="d-flex flex-column gap-2">
                      {analysisSteps.map((label, i) => (
                        <div
                          key={i}
                          className={`analysis-step ${
                            i < analysisStep
                              ? "analysis-step--completed"
                              : i === analysisStep
                                ? "analysis-step--active"
                                : "analysis-step--pending"
                          }`}
                        >
                          <span className="analysis-step__icon">
                            {i < analysisStep ? (
                              <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                                <path d="M13.485 3.929a1 1 0 0 1 .086 1.406l-6 7a1 1 0 0 1-1.48.055l-3-3a1 1 0 0 1 1.41-1.42l2.216 2.217 5.338-6.214a1 1 0 0 1 1.43-.044Z" />
                              </svg>
                            ) : i === analysisStep ? (
                              <div className="spinner-border spinner-border-sm" role="status">
                                <span className="visually-hidden">{t("common.loading")}</span>
                              </div>
                            ) : (
                              <span className="analysis-step__dot" />
                            )}
                          </span>
                          <span className="analysis-step__label">{label}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              ) : null}

              {!analysisState.loading && analysisState.error ? (
                <div className="alert alert-danger" role="alert">
                  {analysisState.error}
                </div>
              ) : null}

              {!analysisState.loading &&
              !analysisState.error &&
              hasResults &&
              analysisResult ? (
                <div className="analysis-results d-flex flex-column gap-4">
                  <div className="d-flex justify-content-end no-print">
                    <button
                      type="button"
                      className="btn btn-outline-secondary btn-sm d-flex align-items-center gap-1"
                      onClick={() => window.print()}
                      title={t("common.print")}
                    >
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <polyline points="6 9 6 2 18 2 18 9" />
                        <path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2" />
                        <rect x="6" y="14" width="12" height="8" />
                      </svg>
                      {t("common.print")}
                    </button>
                  </div>
                  {bestDates ? (
                    <div className="card shadow-sm">
                      <div className="card-header d-flex align-items-center justify-content-between">
                        <h3 className="h5 mb-0">{t("app.bestDates")}</h3>
                        <button
                          type="button"
                          className="btn btn-outline-primary btn-sm"
                          onClick={() => {
                            if (bestDates.preBest) setPreFireInput(bestDates.preBest);
                            if (bestDates.postBest) setPostFireInput(bestDates.postBest);
                          }}
                        >
                          {t("app.useBestDates")}
                        </button>
                      </div>
                      <div className="card-body">
                        <dl className="row mb-0">
                          {bestDates.preBest ? (
                            <>
                              <dt className="text-muted small col-sm-4">{t("app.preFire")}</dt>
                              <dd className="col-sm-8 mb-2">{bestDates.preBest}</dd>
                            </>
                          ) : null}
                          {bestDates.postBest ? (
                            <>
                              <dt className="text-muted small col-sm-4">{t("app.postFire")}</dt>
                              <dd className="col-sm-8 mb-0">{bestDates.postBest}</dd>
                            </>
                          ) : null}
                        </dl>
                      </div>
                    </div>
                  ) : null}

                  {severityEntries.length ? (
                    <div className="card shadow-sm">
                      <div className="card-header d-flex align-items-center justify-content-between">
                        <h3 className="h5 mb-0">{t("app.severityTitle")}</h3>
                        <button
                          type="button"
                          className="btn btn-outline-secondary btn-sm d-flex align-items-center gap-1"
                          onClick={handleDownloadSeverityCsv}
                          title={t("common.downloadCsv")}
                        >
                          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                            <polyline points="7 10 12 15 17 10" />
                            <line x1="12" y1="15" x2="12" y2="3" />
                          </svg>
                          CSV
                        </button>
                      </div>
                      <div className="card-body">
                        <div className="table-responsive">
                          <table className="table table-hover mb-0">
                            <thead className="table-light">
                              <tr>
                                <th scope="col">{t("app.severity")}</th>
                                <th scope="col">{t("app.areaHa")}</th>
                                <th scope="col">{t("app.percent")}</th>
                              </tr>
                            </thead>
                            <tbody>
                              {severityEntries.map(({ name, area, percent }) => (
                                <tr key={name}>
                                  <td>
                                    <span className="d-flex align-items-center gap-2">
                                      {severityColorMap[name] && (
                                        <span
                                          className="d-inline-block rounded severity-color"
                                          style={{
                                            width: "12px",
                                            height: "12px",
                                            backgroundColor: severityColorMap[name],
                                          }}
                                        />
                                      )}
                                      {severityTranslationMap[name] || name}
                                    </span>
                                  </td>
                                  <td>{formatAreaValue(area)}</td>
                                  <td>{formatPercentValue(percent)}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    </div>
                  ) : null}

                  {imageEntries.length ? (
                    <div className="card shadow-sm">
                      <div className="card-header">
                        <h3 className="h5 mb-0">{t("app.visualizations")}</h3>
                      </div>
                      <div className="card-body">
                        <div className="row g-3">
                          {imageEntries.map(([key, url]) => (
                            <div className="col-md-6 col-lg-4" key={key}>
                              <div className="text-center">
                                <div className="fw-semibold mb-2">{formatLabel(key)}</div>
                                <a href={url} target="_blank" rel="noopener noreferrer">
                                  <img
                                    src={url}
                                    alt={formatLabel(key)}
                                    className="img-fluid rounded border"
                                    style={{ maxHeight: "300px" }}
                                    loading="lazy"
                                  />
                                </a>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  ) : null}

                  {tiffEntries.length || csvEntry ? (
                    <div className="card shadow-sm no-print">
                      <div className="card-header">
                        <h3 className="h5 mb-0">{t("app.downloads")}</h3>
                      </div>
                      <div className="card-body">
                        <div className="d-flex flex-wrap gap-2">
                          {tiffEntries.map(([key, url]) => (
                            <a
                              key={key}
                              href={url}
                              className="btn btn-outline-secondary btn-sm"
                              target="_blank"
                              rel="noopener noreferrer"
                            >
                              {formatLabel(key)} (TIFF)
                            </a>
                          ))}
                          {csvEntry ? (
                            <a
                              href={csvEntry[1]}
                              className="btn btn-outline-secondary btn-sm"
                              target="_blank"
                              rel="noopener noreferrer"
                            >
                              {formatLabel(csvEntry[0])} (CSV)
                            </a>
                          ) : null}
                        </div>
                      </div>
                    </div>
                  ) : null}

                  <div className="card shadow-sm no-print">
                    <div className="card-header">
                      <h3 className="h5 mb-0">{t("app.viewJson")}</h3>
                    </div>
                    <div className="card-body">
                      <details>
                        <summary className="fw-medium mb-2">
                          {t("app.viewJson")}
                        </summary>
                        <pre className="mb-0 bg-light p-3 rounded overflow-auto">
                          {JSON.stringify(analysisResult, null, 2)}
                        </pre>
                      </details>
                    </div>
                  </div>

                  <div className="card shadow-sm no-print">
                    <div className="card-header">
                      <h3 className="h5 mb-0">{t("app.deliverableTitle")}</h3>
                    </div>
                    <div className="card-body">
                      <p className="small text-muted mb-3">
                        {t("app.deliverableHint")}
                      </p>
                      <div className="d-flex flex-wrap gap-3">
                        {scientificDeliverables.map(({ label, value }) => {
                          const status = deliverableStatus[value] || {};
                          const deliverableUrl = status.url;
                          const isProcessing = status.loading || status.polling;
                          const cardClass = deliverableUrl
                            ? "is-ready"
                            : isProcessing
                              ? "is-processing"
                              : status.error
                                ? "is-error"
                                : "";

                          return (
                            <div
                              key={value}
                              className={`card shadow-sm deliverable-card ${cardClass}`}
                            >
                              <div className="card-body py-3 px-3">
                                <div className="fw-semibold small mb-2">{label}</div>
                                {deliverableUrl ? (
                                  <a
                                    href={deliverableUrl}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="btn btn-sm btn-outline-success d-inline-flex align-items-center gap-1"
                                  >
                                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                      <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
                                      <polyline points="15 3 21 3 21 9" />
                                      <line x1="10" y1="14" x2="21" y2="3" />
                                    </svg>
                                    {t("app.deliverableOpen")}
                                  </a>
                                ) : isProcessing ? (
                                  <div className="d-flex align-items-center gap-2 text-muted small">
                                    <div className="spinner-border spinner-border-sm" role="status">
                                      <span className="visually-hidden">{t("common.loading")}</span>
                                    </div>
                                    {t("app.deliverableProcessing")}
                                  </div>
                                ) : status.error ? (
                                  <div>
                                    <div className="small text-danger mb-1">{status.error}</div>
                                    <button
                                      type="button"
                                      className="btn btn-sm btn-outline-secondary"
                                      disabled={isScientificDeliverableDisabled}
                                      onClick={() => handleScientificDeliverable(value)}
                                    >
                                      {t("common.tryAgain")}
                                    </button>
                                  </div>
                                ) : (
                                  <button
                                    type="button"
                                    className="btn btn-sm btn-outline-primary"
                                    disabled={isScientificDeliverableDisabled}
                                    onClick={() => handleScientificDeliverable(value)}
                                    title={t("app.deliverableTooltip", { label })}
                                  >
                                    {t("app.deliverableRequest")}
                                  </button>
                                )}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  </div>
                </div>
              ) : null}

              {!analysisState.loading &&
              !analysisState.error &&
              !analysisResult ? (
                <div className="placeholder-card border border-dashed rounded-3 p-5 text-center text-muted bg-white">
                  <p className="mb-0">{t("app.selectParamsHint")}</p>
                </div>
              ) : null}
            </section>
          ) : (
            <section className="app-main-content p-4 flex-grow-1">
              <div className="alert alert-warning" role="alert">
                {t("app.backendUnauthorized")}
              </div>
            </section>
          )}
            </div>
          )}
        </main>
      </div>

      {/* AI Analysis floating button and modal - only on analysis page */}
      {currentPage === "analysis" && (
        <AIAnalysisModal
          isVisible={hasResults && severityEntries.length > 0}
          preFireDate={preFireDate}
          postFireDate={postFireDate}
          areaOfInterest={selectedReserveName}
          severityDistribution={severityDistributionForAPI}
          imageUrls={imageEntries.map(([key, url]) => ({ label: formatLabel(key), url }))}
          authorizedFetch={authorizedFetch}
          baseUrl={baseUrl}
        />
      )}

      <footer className="app-footer mt-auto py-3 text-center small">
        <div className="container-fluid">
          {t("app.footer", { version: UI_VERSION })}
        </div>
      </footer>
    </div>
  );
}

export default App;
