import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useAuth0 } from "@auth0/auth0-react";
import "./App.css";
import AIAnalysisModal from "./AIAnalysisModal";
import LandingPage from "./LandingPage";
import { useLanguage } from "./LanguageContext";
import LanguageSelector from "./LanguageSelector";
import AreasOfInterest from "./AreasOfInterest";
import UserProfile from "./UserProfile";

const UI_VERSION = "1.3.0";

function App() {
  const { t, language } = useLanguage();
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
  const [hasResults, setHasResults] = useState(false);
  const [deliverableStatus, setDeliverableStatus] = useState({});
  const [deliverableAlert, setDeliverableAlert] = useState(null);
  const [isNavOpen, setIsNavOpen] = useState(false);
  const [backendProfile, setBackendProfile] = useState(null);
  const [showLandingPage, setShowLandingPageState] = useState(
    () => sessionStorage.getItem("showLandingPage") === "true"
  );
  const setShowLandingPage = useCallback((value) => {
    setShowLandingPageState(value);
    if (value) {
      sessionStorage.setItem("showLandingPage", "true");
    } else {
      sessionStorage.removeItem("showLandingPage");
    }
  }, []);

  // Page navigation state: "home", "analysis", or "areas"
  const [currentPage, setCurrentPage] = useState("home");

  const toggleNav = useCallback(() => {
    setIsNavOpen((previous) => !previous);
  }, []);

  const closeNav = useCallback(() => {
    setIsNavOpen(false);
  }, []);

  const navigateTo = useCallback((page) => {
    setCurrentPage(page);
    setIsNavOpen(false);
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
  const preFirePickerRef = useRef(null);
  const postFirePickerRef = useRef(null);

  const authReady = !authLoading && isAuthenticated;

  const login = useCallback(
    () => loginWithRedirect({ authorizationParams: { ui_locales: language } }),
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

  useEffect(() => {
    if (!authReady || !baseUrl) return;

    (async () => {
      try {
        const data = await fetchBackendProfile();
        if (data) {
          const backendLang = data.default_language;
          if (backendLang && backendLang !== language) {
            authorizedFetch(`${baseUrl}/me/`, {
              method: "PATCH",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ default_language: language }),
            }).catch((err) =>
              console.error("Failed to sync language to backend:", err)
            );
          }
        }
      } finally {
        languageLoadedRef.current = true;
      }
    })();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authReady, baseUrl]);

  // Persist language changes to backend (after initial sync)
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
          `${baseUrl}/area_of_interest/`,
          {
            signal: controller.signal,
          }
        );

        ensureAuthorizedResponse(response);

        if (!response.ok) {
          throw new Error(t("app.errorLoadingReserves", { status: response.status }));
        }

        const data = await response.json();
        setAreasOfInterest(data);
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

  const formatIsoInput = useCallback((rawValue) => {
    if (!rawValue) {
      return "";
    }

    const digits = rawValue.replace(/[^0-9]/g, "").slice(0, 8);
    if (!digits) {
      return "";
    }

    if (digits.length <= 4) {
      return digits;
    }

    if (digits.length <= 6) {
      return `${digits.slice(0, 4)}-${digits.slice(4)}`;
    }

    return `${digits.slice(0, 4)}-${digits.slice(4, 6)}-${digits.slice(6)}`;
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
      "Unburned": "green",
      "Low Severity": "yellow",
      "Moderate Severity": "orange",
      "High Severity": "red",
      "Very High Severity": "purple"
    }),
    []
  );

  const getSeverityColor = useCallback(
    (name) => severityColorMap[name] || "",
    [severityColorMap]
  );

  const scientificDeliverables = useMemo(
    () => [
      { label: "RGB pre-fire", value: "RGB_PRE_FIRE" },
      { label: "RGB post-fire", value: "RGB_POST_FIRE" },
      { label: "dNBR", value: "DNBR" },
      { label: "RBR", value: "RBR" },
      { label: "dNDVI", value: "DNDVI" },
    ],
    []
  );

  const scientificDeliverableLabels = useMemo(
    () =>
      scientificDeliverables.reduce((accumulator, item) => {
        // eslint-disable-next-line no-param-reassign
        accumulator[item.value] = item.label;
        return accumulator;
      }, {}),
    [scientificDeliverables]
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

  const handleScientificDeliverable = useCallback(
    async (deliverableName) => {
      if (isScientificDeliverableDisabled) {
        return;
      }

      setDeliverableAlert(null);
      updateDeliverableStatus(deliverableName, {
        loading: true,
        error: null,
        taskId: null,
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

        const url = `${baseUrl}/area_of_interest/${selectedReserve}/scientific_deliverable/?${queryParams.toString()}`;

        const response = await authorizedFetch(url, { method: "POST" });
        ensureAuthorizedResponse(response);

        if (!response.ok) {
          throw new Error(t("app.errorDeliverable", { status: response.status }));
        }

        const data = await response.json();
        const readableLabel =
          scientificDeliverableLabels[deliverableName] || deliverableName;
        updateDeliverableStatus(deliverableName, {
          loading: false,
          taskId: data.task_id || null,
        });
        setDeliverableAlert({
          type: "success",
          message: t("app.deliverableSuccess", { label: readableLabel }),
        });
      } catch (error) {
        console.error("Failed to request scientific deliverable:", error);
        updateDeliverableStatus(deliverableName, {
          loading: false,
          error: error.message || "Unknown error",
          taskId: null,
        });
        const readableLabel =
          scientificDeliverableLabels[deliverableName] || deliverableName;
        setDeliverableAlert({
          type: "danger",
          message: t("app.deliverableFailed", { label: readableLabel, error: error.message || "Unknown error" }),
        });
      }
    },
    [
      authorizedFetch,
      baseUrl,
      ensureAuthorizedResponse,
      isScientificDeliverableDisabled,
      preFireDate,
      postFireDate,
      selectedReserve,
      scientificDeliverableLabels,
      updateDeliverableStatus,
      t,
    ]
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
    setDeliverableStatus({});
    setDeliverableAlert(null);

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
    return <LandingPage onLogin={login} />;
  }

  if (showLandingPage) {
    return (
      <LandingPage
        isAuthenticated
        onLogin={() => setShowLandingPage(false)}
      />
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
              className="btn p-0 border-0 bg-transparent"
              onClick={() => setShowLandingPage(true)}
              aria-label={t("landing.title")}
            >
              <img
                src={logoSrc}
                alt={t("landing.title")}
                className="brand-logo"
              />
            </button>
            <div className="d-none d-md-block">
              <h1 className="h4 mb-1">{t("app.title")}</h1>
              <p className="mb-0 small opacity-75">
                {t("app.subtitle")}
              </p>
            </div>
          </div>

          <div className="d-flex align-items-center gap-2 header-actions">
            <LanguageSelector className="form-select form-select-sm bg-transparent text-white border-light" />
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
        <nav className={`nav-sidebar ${isNavOpen ? "is-open" : ""}`}>
          <div className="nav-sidebar-header d-flex justify-content-between align-items-center p-3">
            <span className="fw-semibold">{t("app.title")}</span>
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
        </nav>

        {/* Main Content */}
        <main className="app-main flex-grow-1 d-flex flex-column">
          {currentPage === "home" ? (
            <section className="app-main-content p-4 flex-grow-1 d-flex align-items-center justify-content-center">
              <div className="text-center">
                <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="#6c757d" strokeWidth="1.5" className="mb-4">
                  <line x1="3" y1="12" x2="21" y2="12" />
                  <line x1="3" y1="6" x2="21" y2="6" />
                  <line x1="3" y1="18" x2="21" y2="18" />
                </svg>
                <h2 className="h4 text-muted mb-3">{t("app.welcomeTitle")}</h2>
                <p className="text-muted mb-0">{t("app.welcomeMessage")}</p>
              </div>
            </section>
          ) : currentPage === "areas" ? (
            <AreasOfInterest
              authorizedFetch={authorizedFetch}
              baseUrl={baseUrl}
            />
          ) : currentPage === "profile" ? (
            <UserProfile
              authorizedFetch={authorizedFetch}
              baseUrl={baseUrl}
              user={user}
              backendProfile={backendProfile}
              onProfileUpdate={fetchBackendProfile}
            />
          ) : !backendAuthorizationError ? (
            <section className="app-main-content p-4 flex-grow-1">
              {backendAuthorizationError ? (
                <div className="alert alert-warning" role="alert">
                  {t("app.backendUnauthorized")}
                </div>
              ) : null}

              {/* Analysis Form Card */}
              <div className="card shadow-sm mb-4">
                <div className="card-header bg-white">
                  <h2 className="h5 mb-0">{t("app.analysisParams")}</h2>
                </div>
                <div className="card-body">
                  <form onSubmit={handleSubmit}>
                    <div className="row g-3">
                      <div className="col-12 col-md-6 col-lg-3">
                        <label htmlFor="preFireDate" className="form-label">
                          {t("app.preFireDate")}
                        </label>
                        <div className="date-input-wrapper">
                          <input
                            type="text"
                            className="form-control date-input-text"
                            id="preFireDate"
                            name="preFireDate"
                            placeholder="YYYY-MM-DD"
                            value={preFireInput}
                            onChange={(event) =>
                              setPreFireInput(formatIsoInput(event.target.value))
                            }
                          />
                          <button
                            type="button"
                            className="btn btn-outline-secondary date-picker-button"
                            aria-label={t("app.preFireDate")}
                            onClick={() =>
                              preFirePickerRef.current?.showPicker?.() ||
                              preFirePickerRef.current?.focus()
                            }
                          >
                            {t("common.pick")}
                          </button>
                          <input
                            ref={preFirePickerRef}
                            type="date"
                            className="date-input-native"
                            value={preFireDate}
                            onChange={(event) =>
                              setPreFireInput(normalizeDateValue(event.target.value))
                            }
                            max={postFireDate || undefined}
                          />
                        </div>
                      </div>

                      <div className="col-12 col-md-6 col-lg-3">
                        <label htmlFor="postFireDate" className="form-label">
                          {t("app.postFireDate")}
                        </label>
                        <div className="date-input-wrapper">
                          <input
                            type="text"
                            className="form-control date-input-text"
                            id="postFireDate"
                            name="postFireDate"
                            placeholder="YYYY-MM-DD"
                            value={postFireInput}
                            onChange={(event) =>
                              setPostFireInput(formatIsoInput(event.target.value))
                            }
                          />
                          <button
                            type="button"
                            className="btn btn-outline-secondary date-picker-button"
                            aria-label={t("app.postFireDate")}
                            onClick={() =>
                              postFirePickerRef.current?.showPicker?.() ||
                              postFirePickerRef.current?.focus()
                            }
                          >
                            {t("common.pick")}
                          </button>
                          <input
                            ref={postFirePickerRef}
                            type="date"
                            className="date-input-native"
                            value={postFireDate}
                            onChange={(event) =>
                              setPostFireInput(normalizeDateValue(event.target.value))
                            }
                            min={preFireDate || undefined}
                          />
                        </div>
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
                <div className="placeholder-card border border-dashed rounded-3 p-5 text-center bg-white">
                  <div className="spinner-border text-primary mb-3" role="status">
                    <span className="visually-hidden">{t("common.loading")}</span>
                  </div>
                  <p className="mb-0">{t("app.processing")}</p>
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
                  {bestDates ? (
                    <div className="card border-0 shadow-sm">
                      <div className="card-body">
                        <h3 className="card-title h5 mb-3">
                          {t("app.bestDates")}
                        </h3>
                        <dl className="row mb-0">
                          {bestDates.preBest ? (
                            <>
                              <dt className="col-sm-4">{t("app.preFire")}</dt>
                              <dd className="col-sm-8">{bestDates.preBest}</dd>
                            </>
                          ) : null}
                          {bestDates.postBest ? (
                            <>
                              <dt className="col-sm-4">{t("app.postFire")}</dt>
                              <dd className="col-sm-8">{bestDates.postBest}</dd>
                            </>
                          ) : null}
                        </dl>
                      </div>
                    </div>
                  ) : null}

                  {imageEntries.length ? (
                    <section>
                      <h3 className="h5 mb-3">{t("app.visualizations")}</h3>
                      <div className="analysis-images row g-4">
                        {imageEntries.map(([key, url]) => (
                          <div className="col-12 col-md-6 col-lg-4" key={key}>
                            <div className="card h-100 shadow-sm">
                              <img
                                src={url}
                                className="card-img-top"
                                alt={formatLabel(key)}
                                loading="lazy"
                              />
                              <div className="card-body">
                                <h4 className="card-title h6 mb-0">
                                  {formatLabel(key)}
                                </h4>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </section>
                  ) : null}

                  {severityEntries.length ? (
                    <section>
                      <h3 className="h5 mb-3">{t("app.severityTitle")}</h3>
                      <div className="table-responsive">
                        <table className="table table-sm table-striped align-middle">
                          <thead className="table-light">
                            <tr>
                              <th scope="col">{t("app.severity")}</th>
                              <th scope="col">{t("app.areaHa")}</th>
                              <th scope="col">{t("app.percent")}</th>
                              <th scope="col">{t("app.color")}</th>
                            </tr>
                          </thead>
                          <tbody>
                            {severityEntries.map(({ name, area, percent }) => (
                              <tr key={name}>
                                <td>{name}</td>
                                <td>{formatAreaValue(area)}</td>
                                <td>{formatPercentValue(percent)}</td>
                                <td>{getSeverityColor(name)}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </section>
                  ) : null}

                  {tiffEntries.length || csvEntry ? (
                    <section>
                      <h3 className="h5 mb-3">{t("app.downloads")}</h3>
                      <div className="analysis-downloads d-flex flex-wrap gap-2">
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
                    </section>
                  ) : null}

                  <section>
                    <details className="analysis-raw border rounded-3 p-3 bg-white shadow-sm">
                      <summary className="fw-medium mb-2">
                        {t("app.viewJson")}
                      </summary>
                      <pre className="mb-0 bg-light p-3 rounded overflow-auto">
                        {JSON.stringify(analysisResult, null, 2)}
                      </pre>
                    </details>
                  </section>

                  <section className="mt-4">
                    <h3 className="h5 mb-2">{t("app.deliverableTitle")}</h3>
                    <p className="small text-muted mb-3">
                      {t("app.deliverableHint")}
                    </p>
                    <div className="d-flex flex-wrap gap-3">
                      {scientificDeliverables.map(({ label, value }) => {
                        const status = deliverableStatus[value] || {};
                        return (
                          <div
                            key={value}
                            className="d-flex flex-column align-items-start"
                          >
                            <button
                              type="button"
                              className="btn btn-link p-0"
                              disabled={
                                isScientificDeliverableDisabled || status.loading
                              }
                              onClick={() => handleScientificDeliverable(value)}
                              title={t("app.deliverableTooltip", { label })}
                            >
                              {status.loading
                                ? t("app.deliverableRequesting", { label })
                                : label}
                            </button>
                            {status.taskId ? (
                              <span className="small text-success">
                                {t("app.taskId", { taskId: status.taskId })}
                              </span>
                            ) : null}
                            {!status.loading && status.error ? (
                              <span className="small text-danger">
                                {status.error}
                              </span>
                            ) : null}
                          </div>
                        );
                      })}
                    </div>
                    {deliverableAlert ? (
                      <div
                        className={`alert alert-${deliverableAlert.type} mt-3`}
                        role="alert"
                      >
                        {deliverableAlert.message}
                      </div>
                    ) : null}
                  </section>
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
