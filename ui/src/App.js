import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useAuth0 } from "@auth0/auth0-react";
import "./App.css";

const BACKEND_UNAUTHORIZED_MESSAGE =
  "Your account is already authenticated, but it has not been authorized on our backend servers yet. Contact an administrator.";

function App() {
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
  const [ecologicalReserves, setEcologicalReserves] = useState([]);
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
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  const toggleSidebar = useCallback(() => {
    setIsSidebarOpen((previous) => !previous);
  }, []);

  const closeSidebar = useCallback(() => {
    setIsSidebarOpen(false);
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

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      loginWithRedirect().catch((error) => {
        console.error("Failed to redirect to Auth0:", error);
      });
    }
  }, [authLoading, isAuthenticated, loginWithRedirect]);

  const authReady = !authLoading && isAuthenticated;

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
        throw new Error(BACKEND_UNAUTHORIZED_MESSAGE);
      }
      return response;
    },
    [setBackendAuthorizationError]
  );

  const loadReserves = useCallback(() => {
    if (!baseUrl) {
      setFetchState({
        loading: false,
        error:
          "Environment variable REACT_APP_WILDLIFE_API_URL is not configured.",
      });
      return undefined;
    }

    const controller = new AbortController();

    setFetchState({ loading: true, error: null });

    (async () => {
      try {
        const response = await authorizedFetch(
          `${baseUrl}/ecological_reserve/`,
          {
            signal: controller.signal,
          }
        );

        ensureAuthorizedResponse(response);

        if (!response.ok) {
          throw new Error(`Error loading reserves (${response.status})`);
        }

        const data = await response.json();
        setEcologicalReserves(data);
        setFetchState({ loading: false, error: null });
      } catch (error) {
        if (error.name === "AbortError") return;

        console.error("Failed to fetch ecological reserves:", error);
        setFetchState({ loading: false, error: error.message });
      }
    })();

    return () => controller.abort();
  }, [authorizedFetch, baseUrl, ensureAuthorizedResponse]);

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
          Loading reserves...
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

    if (!ecologicalReserves.length) {
      return (
        <option value="" disabled>
          No reserves found.
        </option>
      );
    }

    return [
      <option key="placeholder" value="" disabled>
        Choose an option
      </option>,
      ...ecologicalReserves.map((reserve) => (
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
          throw new Error("API endpoint is not configured.");
        }

        const queryParams = new URLSearchParams({
          pre_fire_date: preFireDate,
          post_fire_date: postFireDate,
          deliverable: deliverableName,
        });

        const url = `${baseUrl}/ecological_reserve/${selectedReserve}/scientific_deliverable/?${queryParams.toString()}`;

        const response = await authorizedFetch(url, { method: "POST" });
        ensureAuthorizedResponse(response);

        if (!response.ok) {
          throw new Error(`Error requesting deliverable (${response.status})`);
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
          message: `You will receive an email with the ${readableLabel} download link as soon as it is ready.`,
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
          message: `Failed to request ${readableLabel}: ${error.message || "Unknown error"}`,
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
        error: "API endpoint is not configured.",
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
    closeSidebar();

    try {
      const queryParams = new URLSearchParams({
        pre_fire_date: preFireDate,
        post_fire_date: postFireDate,
      });
      const url = `${baseUrl}/ecological_reserve/${selectedReserve}/analyze/?${queryParams.toString()}`;

      const response = await authorizedFetch(url, {
        method: "POST",
        signal: controller.signal,
      });

      ensureAuthorizedResponse(response);

      if (!response.ok) {
        throw new Error(`Error running analysis (${response.status})`);
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

  if (authError) {
    return (
      <div className="app-root d-flex align-items-center justify-content-center min-vh-100">
        <div className="alert alert-danger m-4" role="alert">
          {authError.message || "Authentication failed."}
          <div className="mt-3">
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => loginWithRedirect()}
            >
              Try again
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!authReady) {
    return (
      <div className="app-root d-flex align-items-center justify-content-center min-vh-100">
        <div className="text-center">
          <div className="spinner-border text-primary mb-3" role="status">
            <span className="visually-hidden">Authenticating...</span>
          </div>
          <p className="mb-0">Redirecting to the login page...</p>
        </div>
      </div>
    );
  }

  const displayName = user?.name || user?.email || "User";

  return (
    <div className="app-root d-flex flex-column min-vh-100">
      <header className="app-header text-white">
        <div className="container-fluid d-flex align-items-center justify-content-between py-3 gap-3">
          <div className="d-flex align-items-center gap-3 flex-shrink-0">
            <img
              src={logoSrc}
              alt="Wildfire Assessment"
              className="brand-logo"
            />
            <div className="d-none d-md-block">
              <h1 className="h4 mb-1">Wildfire assessment</h1>
              <p className="mb-0 small opacity-75">
                Monitoring areas affected before and after fire events
              </p>
            </div>
          </div>
          <div className="d-flex align-items-center gap-2 header-actions">
            <div className="text-end d-none d-md-block">
              <p className="mb-0 small opacity-75">Signed in as</p>
              <strong className="small">{displayName}</strong>
            </div>
            <button
              type="button"
              className="btn btn-outline-light btn-sm"
              onClick={() =>
                logout({ logoutParams: { returnTo: window.location.origin } })
              }
            >
              Logout
            </button>
            <button
              type="button"
              className="btn btn-outline-light btn-sm mobile-sidebar-toggle d-lg-none"
              onClick={toggleSidebar}
              aria-label="Open filters"
            >
              <span className="mobile-sidebar-icon" aria-hidden="true"></span>
            </button>
          </div>
        </div>
      </header>

      <div className="app-body d-flex flex-grow-1">
        {!backendAuthorizationError ? (
          <>
            {isSidebarOpen ? (
              <button
                type="button"
                className="sidebar-backdrop d-lg-none"
                onClick={closeSidebar}
                aria-label="Close filters"
              >
                <span className="visually-hidden">Close filters</span>
              </button>
            ) : null}
            <aside
              className={`sidebar bg-light border-end p-4 ${
                isSidebarOpen ? "is-open" : ""
              }`}
            >
              <div className="d-flex justify-content-between align-items-center d-lg-none mb-3">
                <h1 className="h5 mb-0">Analysis parameters</h1>
                <button
                  type="button"
                  className="btn btn-outline-secondary btn-sm"
                  onClick={closeSidebar}
                >
                  Close
                </button>
              </div>
              <h1 className="h5 mb-4 d-none d-lg-block">Analysis parameters</h1>
              <form onSubmit={handleSubmit}>
              <div className="mb-3">
                <label htmlFor="preFireDate" className="form-label">
                  Pre-fire date
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
                    aria-label="Open calendar for pre-fire date"
                    onClick={() =>
                      preFirePickerRef.current?.showPicker?.() ||
                      preFirePickerRef.current?.focus()
                    }
                  >
                    Pick
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

              <div className="mb-3">
                <label htmlFor="postFireDate" className="form-label">
                  Post-fire date
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
                    aria-label="Open calendar for post-fire date"
                    onClick={() =>
                      postFirePickerRef.current?.showPicker?.() ||
                      postFirePickerRef.current?.focus()
                    }
                  >
                    Pick
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

              <div className="mb-3">
                <label htmlFor="reserve" className="form-label">
                  Select the area of interest
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
                      Make sure the API is reachable and that the certificate
                      is trusted. In development environments with self-signed
                      HTTPS, open the endpoint directly in the browser to
                      accept the certificate before using the application.
                    </p>
                    <button
                      type="button"
                      className="btn btn-outline-danger btn-sm"
                      onClick={loadReserves}
                    >
                      Try again
                    </button>
                  </div>
                ) : null}
              </div>

              <button
                type="submit"
                className="btn btn-primary w-100"
                disabled={isAnalyzeDisabled}
              >
                {analysisState.loading ? "Analyzing..." : "Run analysis"}
              </button>

              <div className="mt-4 d-lg-none">
                <button
                  type="button"
                  className="btn btn-outline-secondary w-100"
                  onClick={closeSidebar}
                >
                  Hide menu
                </button>
              </div>
            </form>
            </aside>
          </>
        ) : null}

        <main className="app-main flex-grow-1 d-flex flex-column">
          <section className="app-main-content p-5 flex-grow-1">
            {backendAuthorizationError ? (
              <div className="alert alert-warning" role="alert">
                {BACKEND_UNAUTHORIZED_MESSAGE}
              </div>
            ) : null}

            <div className="alert alert-info d-lg-none" role="alert">
              Use the menu to select the time period and area of interest for your assessment.
            </div>

            {analysisState.loading ? (
              <div className="placeholder-card border border-dashed rounded-3 p-5 text-center">
                <div className="spinner-border text-primary mb-3" role="status">
                  <span className="visually-hidden">Loading...</span>
                </div>
                <p className="mb-0">Processing analysis. This may take a few moments...</p>
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
                        Best dates identified
                      </h3>
                      <dl className="row mb-0">
                        {bestDates.preBest ? (
                          <>
                            <dt className="col-sm-4">Pre-fire</dt>
                            <dd className="col-sm-8">{bestDates.preBest}</dd>
                          </>
                        ) : null}
                        {bestDates.postBest ? (
                          <>
                            <dt className="col-sm-4">Post-fire</dt>
                            <dd className="col-sm-8">{bestDates.postBest}</dd>
                          </>
                        ) : null}
                      </dl>
                    </div>
                  </div>
                ) : null}

                {imageEntries.length ? (
                  <section>
                    <h3 className="h5 mb-3">Generated visualizations</h3>
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
                    <h3 className="h5 mb-3">DNBR Severity Distribution</h3>
                    <div className="table-responsive">
                      <table className="table table-sm table-striped align-middle">
                        <thead className="table-light">
                          <tr>
                            <th scope="col">Severity</th>
                            <th scope="col">Area (ha)</th>
                            <th scope="col">Percent</th>
                          </tr>
                        </thead>
                        <tbody>
                          {severityEntries.map(({ name, area, percent }) => (
                            <tr key={name}>
                              <td>{name}</td>
                              <td>{formatAreaValue(area)}</td>
                              <td>{formatPercentValue(percent)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </section>
                ) : null}

                {tiffEntries.length || csvEntry ? (
                  <section>
                    <h3 className="h5 mb-3">Downloads</h3>
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
                      View full response (JSON)
                    </summary>
                    <pre className="mb-0 bg-light p-3 rounded overflow-auto">
                      {JSON.stringify(analysisResult, null, 2)}
                    </pre>
                  </details>
                </section>

                <section className="mt-4">
                  <h3 className="h5 mb-2">Request scientific deliverables</h3>
                  <p className="small text-muted mb-3">
                    Use the links below to queue a background export. You will
                    receive an email once the deliverable is processed.
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
                            title={`Request a scientifical ${label}`}
                          >
                            {status.loading
                              ? `Requesting ${label}...`
                              : label}
                          </button>
                          {status.taskId ? (
                            <span className="small text-success">
                              Task ID: {status.taskId}
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
              <div className="placeholder-card border border-dashed rounded-3 p-5 text-center text-muted"></div>
            ) : null}
          </section>
        </main>
      </div>
      <footer className="app-footer mt-auto py-3 text-center small">
        <div className="container-fluid">
          UI version 1.0.0 · Wildfire Analyser 0.2.17
        </div>
      </footer>
    </div>
  );
}

export default App;
