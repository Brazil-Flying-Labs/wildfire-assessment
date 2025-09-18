import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import './App.css';

function App() {
  const [ecologicalReserves, setEcologicalReserves] = useState([]);
  const [fetchState, setFetchState] = useState({ loading: true, error: null });
  const [selectedReserve, setSelectedReserve] = useState('');
  const [preFireDate, setPreFireDate] = useState('');
  const [postFireDate, setPostFireDate] = useState('');
  const [analysisResult, setAnalysisResult] = useState(null);
  const [analysisState, setAnalysisState] = useState({ loading: false, error: null });
  const baseUrl = useMemo(() => {
    const url = process.env.REACT_APP_WILDLIFE_API_URL;

    if (!url) {
      return '';
    }

    return url.endsWith('/') ? url.slice(0, -1) : url;
  }, []);
  const analyzeControllerRef = useRef(null);

  const loadReserves = useCallback(() => {
    if (!baseUrl) {
      setFetchState({
        loading: false,
        error: 'Variável de ambiente REACT_APP_WILDLIFE_API_URL não configurada.'
      });
      return undefined;
    }

    const controller = new AbortController();

    setFetchState({ loading: true, error: null });

    (async () => {
      try {
        const response = await fetch(`${baseUrl}/ecological_reserve/`, {
          signal: controller.signal
        });

        if (!response.ok) {
          throw new Error(`Erro ao carregar reservas (${response.status})`);
        }

        const data = await response.json();
        setEcologicalReserves(data);
        setFetchState({ loading: false, error: null });
      } catch (error) {
        if (error.name === 'AbortError') return;

        console.error('Erro ao buscar reservas ecológicas:', error);
        setFetchState({ loading: false, error: error.message });
      }
    })();

    return () => controller.abort();
  }, [baseUrl]);

  useEffect(() => {
    const abort = loadReserves();
    return () => {
      if (typeof abort === 'function') {
        abort();
      }
    };
  }, [loadReserves]);

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
      ))
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
    const withoutSuffix = key.replace(/_(jpg|tif)$/i, '');
    return withoutSuffix
      .split('_')
      .map((word) => {
        if (word.length <= 3) return word.toUpperCase();
        return word.charAt(0).toUpperCase() + word.slice(1);
      })
      .join(' ');
  }, []);

  const imageEntries = useMemo(() => {
    if (!analysisResult) return [];
    return Object.entries(analysisResult).filter(([key, value]) =>
      key.endsWith('_jpg') && typeof value === 'string'
    );
  }, [analysisResult]);

  const tiffEntries = useMemo(() => {
    if (!analysisResult) return [];
    return Object.entries(analysisResult).filter(([key, value]) =>
      key.endsWith('_tif') && typeof value === 'string'
    );
  }, [analysisResult]);

  const csvEntry = useMemo(() => {
    if (!analysisResult) return null;
    const entry = Object.entries(analysisResult).find(
      ([key, value]) => key.endsWith('_stats') && typeof value === 'string'
    );
    return entry || null;
  }, [analysisResult]);

  const [severityStats, setSeverityStats] = useState({ loading: false, error: null, headers: [], rows: [] });

  useEffect(() => {
    async function loadSeverityStats(url) {
      setSeverityStats({ loading: true, error: null, headers: [], rows: [] });

      try {
        const response = await fetch(url);

        if (!response.ok) {
          throw new Error(`Erro ao carregar estatísticas (${response.status})`);
        }

        const text = await response.text();
        const [headerLine, ...lines] = text.trim().split(/\r?\n/);
        const headers = headerLine.split(',').map((item) => item.trim());
        const parsedRows = lines.map((line) => {
          const values = line.split(',').map((item) => item.trim());
          return headers.reduce((accumulator, header, index) => {
            // eslint-disable-next-line no-param-reassign
            accumulator[header] = values[index] ?? '';
            return accumulator;
          }, {});
        });

        setSeverityStats({ loading: false, error: null, headers, rows: parsedRows });
      } catch (error) {
        console.error('Falha ao ler CSV de estatísticas:', error);
        setSeverityStats({ loading: false, error: error.message, headers: [], rows: [] });
      }
    }

    if (csvEntry) {
      loadSeverityStats(csvEntry[1]);
    } else {
      setSeverityStats({ loading: false, error: null, headers: [], rows: [] });
    }
  }, [csvEntry]);

  const bestDates = useMemo(() => {
    if (!analysisResult) return null;
    const { pre_fire_best_date: preBest, post_fire_best_date: postBest } = analysisResult;
    if (!preBest && !postBest) return null;
    return { preBest, postBest };
  }, [analysisResult]);

  const handleSubmit = async (event) => {
    event.preventDefault();

    if (isAnalyzeDisabled) {
      return;
    }

    if (!baseUrl) {
      setAnalysisState({ loading: false, error: 'Endpoint da API não configurado.' });
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
        post_fire_date: postFireDate
      });
      const url = `${baseUrl}/ecological_reserve/${selectedReserve}/analyze/?${queryParams.toString()}`;

      const response = await fetch(
        url,
        {
          method: 'POST',
          signal: controller.signal
        }
      );

      if (!response.ok) {
        throw new Error(`Erro ao analisar (${response.status})`);
      }

      const data = await response.json();
      setAnalysisResult(data);
      setAnalysisState({ loading: false, error: null });
    } catch (error) {
      if (error.name === 'AbortError') {
        if (analyzeControllerRef.current === controller) {
          setAnalysisState({ loading: false, error: null });
        }
        return;
      }

      console.error('Erro durante a análise:', error);
      setAnalysisState({ loading: false, error: error.message });
    } finally {
      if (analyzeControllerRef.current === controller) {
        analyzeControllerRef.current = null;
      }
    }
  };

  return (
    <div className="app-wrapper d-flex min-vh-100">
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
                  Verifique se a API está acessível e se o certificado é confiável. Em ambientes
                  de desenvolvimento com HTTPS autoassinado, abra o endpoint diretamente no
                  navegador para aceitar o certificado antes de usar a aplicação.
                </p>
                <button type="button" className="btn btn-outline-danger btn-sm" onClick={loadReserves}>
                  Tentar novamente
                </button>
              </div>
            ) : null}
          </div>

          <button type="submit" className="btn btn-primary w-100" disabled={isAnalyzeDisabled}>
            {analysisState.loading ? 'Analisando…' : 'Analisar'}
          </button>
        </form>
      </aside>

      <main className="flex-grow-1 p-5">
        <h2 className="h3 mb-3">Avaliação de incêndios florestais</h2>
        <p className="text-muted mb-5">
          Configure as datas e a reserva ecológica no menu lateral para visualizar as análises pós-fogo.
        </p>
        {analysisState.loading ? (
          <div className="placeholder-card border border-dashed rounded-3 p-5 text-center">
            <div className="spinner-border text-primary mb-3" role="status">
              <span className="visually-hidden">Carregando...</span>
            </div>
            <p className="mb-0">Processando análise. Isso pode levar alguns instantes…</p>
          </div>
        ) : null}

        {!analysisState.loading && analysisState.error ? (
          <div className="alert alert-danger" role="alert">
            {analysisState.error}
          </div>
        ) : null}

        {!analysisState.loading && !analysisState.error && analysisResult ? (
          <div className="analysis-results d-flex flex-column gap-4">
            {bestDates ? (
              <div className="card border-0 shadow-sm">
                <div className="card-body">
                  <h3 className="card-title h5 mb-3">Melhores datas identificadas</h3>
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
                        <img src={url} className="card-img-top" alt={formatLabel(key)} loading="lazy" />
                        <div className="card-body">
                          <h4 className="card-title h6 mb-0">{formatLabel(key)}</h4>
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
                        {severityStats.headers.map((header) => (
                          <th key={header} scope="col">
                            {header}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {severityStats.rows.map((row, rowIndex) => (
                        <tr key={`${rowIndex.toString()}-${rowIndex}`}>
                          {severityStats.headers.map((header) => (
                            <td key={header}>{row[header] ?? ''}</td>
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
                <summary className="fw-medium mb-2">Ver resposta completa (JSON)</summary>
                <pre className="mb-0 bg-light p-3 rounded overflow-auto">
                  {JSON.stringify(analysisResult, null, 2)}
                </pre>
              </details>
            </section>
          </div>
        ) : null}

        {!analysisState.loading && !analysisState.error && !analysisResult ? (
          <div className="placeholder-card border border-dashed rounded-3 p-5 text-center text-muted">
            Área principal do mapa e resultados disponível em breve.
          </div>
        ) : null}
      </main>
    </div>
  );
}

export default App;
