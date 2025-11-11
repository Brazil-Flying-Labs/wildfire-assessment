import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useAuth0 } from "@auth0/auth0-react";
import "./App.css";

const BACKEND_UNAUTHORIZED_MESSAGE =
  "Sua conta já está autenticada, mas ainda não foi autorizada nos servidores internos. Contate um administrador.";

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
  const [preFireDate, setPreFireDate] = useState("");
  const [postFireDate, setPostFireDate] = useState("");
  const [analysisResult, setAnalysisResult] = useState(null);
  const [analysisState, setAnalysisState] = useState({
    loading: false,
    error: null,
  });
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

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      loginWithRedirect().catch((error) => {
        console.error("Falha ao redirecionar para o Auth0:", error);
      });
    }
  }, [authLoading, isAuthenticated, loginWithRedirect]);

  const authReady = !authLoading && isAuthenticated;

  const authorizedFetch = useCallback(
    async (url, options = {}) => {
      const token = await getAccessTokenSilently({
        authorizationParams: { audience: authAudience },
      });

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
    [authAudience, getAccessTokenSilently]
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

  const apiOrigin = useMemo(() => {
    if (!baseUrl) return null;
    const originBase =
      typeof window !== "undefined" && window.location
        ? window.location.origin
        : undefined;

    try {
      const resolved = originBase
        ? new URL(baseUrl, originBase)
        : new URL(baseUrl);
      return resolved.origin;
    } catch (error) {
      console.warn("URL base inválida para comparação de origem:", error);
      return null;
    }
  }, [baseUrl]);

  const isApiUrl = useCallback(
    (url) => {
      if (!apiOrigin) return false;
      try {
        const target = new URL(url, apiOrigin);
        return target.origin === apiOrigin;
      } catch (error) {
        return false;
      }
    },
    [apiOrigin]
  );

  const loadReserves = useCallback(() => {
    if (!baseUrl) {
      setFetchState({
        loading: false,
        error:
          "Variável de ambiente REACT_APP_WILDLIFE_API_URL não configurada.",
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
          throw new Error(`Erro ao carregar reservas (${response.status})`);
        }

        const data = await response.json();
        setEcologicalReserves(data);
        setFetchState({ loading: false, error: null });
      } catch (error) {
        if (error.name === "AbortError") return;

        console.error("Erro ao buscar reservas ecológicas:", error);
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

  const renderReserveOptions = () => {
    if (fetchState.loading) {
      return (
        <option value="" disabled>
          Carregando reservas...
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
          Nenhuma reserva encontrada.
        </option>
      );
    }

    return [
      <option key="placeholder" value="" disabled>
        Escolha uma opção
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

  const [severityStats, setSeverityStats] = useState({
    loading: false,
    error: null,
    headers: [],
    rows: [],
  });

  const severityHeaderDefinitions = useMemo(
    () =>
      severityStats.headers.map((header) => ({
        key: header,
        label: header === "Area_ha" ? "ha" : header,
      })),
    [severityStats.headers]
  );

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

  const formatSeverityCell = useCallback(
    (headerKey, value) => {
      if (headerKey === "Area_ha" || headerKey === "ha") {
        return formatAreaValue(value);
      }

      if (headerKey === "Percent") {
        return formatPercentValue(value);
      }

      if (value === null || value === undefined) {
        return "";
      }

      return value;
    },
    [formatAreaValue, formatPercentValue]
  );

  useEffect(() => {
    function loadSeverityStats(url) {
      const controller = new AbortController();
      setSeverityStats({ loading: true, error: null, headers: [], rows: [] });

      (async () => {
        try {
          const fromApi = isApiUrl(url);
          const fetchFn = fromApi ? authorizedFetch : fetch;
          const response = await fetchFn(url, { signal: controller.signal });

          if (fromApi) {
            ensureAuthorizedResponse(response);
          }

          if (!response.ok) {
            throw new Error(`Erro ao carregar estatísticas (${response.status})`);
          }

          const text = await response.text();
          const [headerLine, ...lines] = text.trim().split(/\r?\n/);
          const headers = headerLine.split(",").map((item) => item.trim());
          const parsedRows = lines.map((line) => {
            const values = line.split(",").map((item) => item.trim());
            return headers.reduce((accumulator, header, index) => {
              // eslint-disable-next-line no-param-reassign
              accumulator[header] = values[index] ?? "";
              return accumulator;
            }, {});
          });

          setSeverityStats({
            loading: false,
            error: null,
            headers,
            rows: parsedRows,
          });
        } catch (error) {
          if (error.name === "AbortError") {
            return;
          }
          console.error("Falha ao ler CSV de estatísticas:", error);
          setSeverityStats({
            loading: false,
            error: error.message,
            headers: [],
            rows: [],
          });
        }
      })();

      return () => controller.abort();
    }

    if (csvEntry) {
      if (isApiUrl(csvEntry[1]) && !authReady) {
        return undefined;
      }

      const abort = loadSeverityStats(csvEntry[1]);
      return () => {
        if (typeof abort === "function") {
          abort();
        }
      };
    }

    setSeverityStats({ loading: false, error: null, headers: [], rows: [] });
    return undefined;
  }, [authorizedFetch, csvEntry, ensureAuthorizedResponse, isApiUrl, authReady]);

  const bestDates = useMemo(() => {
    if (!analysisResult) return null;
    const { pre_fire_best_date: preBest, post_fire_best_date: postBest } =
      analysisResult;
    if (!preBest && !postBest) return null;
    return { preBest, postBest };
  }, [analysisResult]);

  const handleSubmit = async (event) => {
    event.preventDefault();

    if (isAnalyzeDisabled) {
      return;
    }

    if (!baseUrl) {
      setAnalysisState({
        loading: false,
        error: "Endpoint da API não configurado.",
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
        throw new Error(`Erro ao analisar (${response.status})`);
      }

      const data = await response.json();
      setAnalysisResult(data);
      setAnalysisState({ loading: false, error: null });
    } catch (error) {
      if (error.name === "AbortError") {
        if (analyzeControllerRef.current === controller) {
          setAnalysisState({ loading: false, error: null });
        }
        return;
      }

      console.error("Erro durante a análise:", error);
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
          {authError.message || "Falha na autenticação."}
          <div className="mt-3">
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => loginWithRedirect()}
            >
              Tentar novamente
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
            <span className="visually-hidden">Autenticando...</span>
          </div>
          <p className="mb-0">Redirecionando para a página de login…</p>
        </div>
      </div>
    );
  }

  const displayName = user?.name || user?.email || "Usuário";

  return (
    <div className="app-root d-flex flex-column min-vh-100">
      <header className="app-header text-white">
        <div className="container-fluid d-flex align-items-center justify-content-between py-3">
          <div className="d-flex align-items-center gap-3">
            <img
              src={logoSrc}
              alt="Wildfire Assessment"
              className="brand-logo"
            />
            <div>
              <h1 className="h4 mb-1">Avaliação de incêndios florestais</h1>
              <p className="mb-0 small opacity-75">
                Monitoramento de áreas afetadas antes e após eventos de fogo
              </p>
            </div>
          </div>
          <div className="d-flex align-items-center gap-3">
            <div className="text-end">
              <p className="mb-0 small opacity-75">Autenticado como</p>
              <strong className="small">{displayName}</strong>
            </div>
            <button
              type="button"
              className="btn btn-outline-light btn-sm"
              onClick={() =>
                logout({ logoutParams: { returnTo: window.location.origin } })
              }
            >
              Sair
            </button>
          </div>
        </div>
      </header>

      <div className="app-body d-flex flex-grow-1">
        {!backendAuthorizationError ? (
          <aside className="sidebar bg-light border-end p-4">
            <h1 className="h5 mb-4">Parâmetros da análise</h1>
            <form onSubmit={handleSubmit}>
              <div className="mb-3">
                <label htmlFor="preFireDate" className="form-label">
                  Data pré-fogo
                </label>
                <input
                  type="date"
                  className="form-control"
                  id="preFireDate"
                  name="preFireDate"
                  value={preFireDate}
                  onChange={(event) => setPreFireDate(event.target.value)}
                  max={postFireDate || undefined}
                />
              </div>

              <div className="mb-3">
                <label htmlFor="postFireDate" className="form-label">
                  Data pós-fogo
                </label>
                <input
                  type="date"
                  className="form-control"
                  id="postFireDate"
                  name="postFireDate"
                  value={postFireDate}
                  onChange={(event) => setPostFireDate(event.target.value)}
                  min={preFireDate || undefined}
                />
              </div>

              <div className="mb-3">
                <label htmlFor="reserve" className="form-label">
                  Selecione uma reserva ecológica
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
                      Verifique se a API está acessível e se o certificado é
                      confiável. Em ambientes de desenvolvimento com HTTPS
                      autoassinado, abra o endpoint diretamente no navegador
                      para aceitar o certificado antes de usar a aplicação.
                    </p>
                    <button
                      type="button"
                      className="btn btn-outline-danger btn-sm"
                      onClick={loadReserves}
                    >
                      Tentar novamente
                    </button>
                  </div>
                ) : null}
              </div>

              <button
                type="submit"
                className="btn btn-primary w-100"
                disabled={isAnalyzeDisabled}
              >
                {analysisState.loading ? "Analisando…" : "Analisar"}
              </button>
            </form>
          </aside>
        ) : null}

        <main className="app-main flex-grow-1 d-flex flex-column">
          <section className="app-main-content p-5 flex-grow-1">
            {backendAuthorizationError ? (
              <div className="alert alert-warning" role="alert">
                {BACKEND_UNAUTHORIZED_MESSAGE}
              </div>
            ) : null}

            {analysisState.loading ? (
              <div className="placeholder-card border border-dashed rounded-3 p-5 text-center">
                <div className="spinner-border text-primary mb-3" role="status">
                  <span className="visually-hidden">Carregando...</span>
                </div>
                <p className="mb-0">
                  Processando análise. Isso pode levar alguns instantes…
                </p>
              </div>
            ) : null}

            {!analysisState.loading && analysisState.error ? (
              <div className="alert alert-danger" role="alert">
                {analysisState.error}
              </div>
            ) : null}

            {!analysisState.loading &&
            !analysisState.error &&
            analysisResult ? (
              <div className="analysis-results d-flex flex-column gap-4">
                {bestDates ? (
                  <div className="card border-0 shadow-sm">
                    <div className="card-body">
                      <h3 className="card-title h5 mb-3">
                        Melhores datas identificadas
                      </h3>
                      <dl className="row mb-0">
                        {bestDates.preBest ? (
                          <>
                            <dt className="col-sm-4">Pré-fogo</dt>
                            <dd className="col-sm-8">{bestDates.preBest}</dd>
                          </>
                        ) : null}
                        {bestDates.postBest ? (
                          <>
                            <dt className="col-sm-4">Pós-fogo</dt>
                            <dd className="col-sm-8">{bestDates.postBest}</dd>
                          </>
                        ) : null}
                      </dl>
                    </div>
                  </div>
                ) : null}

                {imageEntries.length ? (
                  <section>
                    <h3 className="h5 mb-3">Visualizações geradas</h3>
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

                {severityStats.headers.length && severityStats.rows.length ? (
                  <section>
                    <h3 className="h5 mb-3">Distribuição da severidade</h3>
                    <div className="table-responsive">
                      <table className="table table-sm table-striped align-middle">
                        <thead className="table-light">
                          <tr>
                            {severityHeaderDefinitions.map(({ key, label }) => (
                              <th key={key} scope="col">
                                {label}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {severityStats.rows.map((row, rowIndex) => (
                            <tr key={`${rowIndex.toString()}-${rowIndex}`}>
                              {severityHeaderDefinitions.map(({ key }) => (
                                <td key={key}>{formatSeverityCell(key, row[key])}</td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </section>
                ) : null}

                {severityStats.loading ? (
                  <div className="alert alert-info" role="status">
                    Carregando estatísticas de severidade...
                  </div>
                ) : null}

                {!severityStats.loading && severityStats.error ? (
                  <div className="alert alert-warning" role="alert">
                    {severityStats.error}
                  </div>
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
                      Ver resposta completa (JSON)
                    </summary>
                    <pre className="mb-0 bg-light p-3 rounded overflow-auto">
                      {JSON.stringify(analysisResult, null, 2)}
                    </pre>
                  </details>
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
    </div>
  );
}

export default App;
