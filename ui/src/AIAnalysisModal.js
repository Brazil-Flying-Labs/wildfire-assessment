import { useCallback, useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";

/**
 * AI Analysis floating button and modal component.
 * Only visible for authorized test users.
 */
function AIAnalysisModal({
  isVisible,
  preFireDate,
  postFireDate,
  areaOfInterest,
  severityDistribution,
  authorizedFetch,
  baseUrl,
}) {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [analysisText, setAnalysisText] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const abortControllerRef = useRef(null);
  const contentRef = useRef(null);

  // Auto-scroll to bottom as content streams in
  useEffect(() => {
    if (contentRef.current && analysisText) {
      contentRef.current.scrollTop = contentRef.current.scrollHeight;
    }
  }, [analysisText]);

  const openModal = useCallback(() => {
    setIsModalOpen(true);
    setAnalysisText("");
    setError(null);
  }, []);

  const closeModal = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsModalOpen(false);
    setIsLoading(false);
  }, []);

  const startAnalysis = useCallback(async () => {
    if (!baseUrl || isLoading) return;

    // Abort any existing request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    const controller = new AbortController();
    abortControllerRef.current = controller;

    setIsLoading(true);
    setAnalysisText("");
    setError(null);

    try {
      const response = await authorizedFetch(`${baseUrl}/analysis/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          pre_fire_date: preFireDate,
          post_fire_date: postFireDate,
          area_of_interest: areaOfInterest,
          severity_distribution: severityDistribution,
        }),
        signal: controller.signal,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || `HTTP ${response.status}`);
      }

      // Read the streaming response
      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        setAnalysisText((prev) => prev + chunk);
      }
    } catch (err) {
      if (err.name === "AbortError") {
        return;
      }
      console.error("AI Analysis error:", err);
      setError(err.message || "Failed to generate analysis");
    } finally {
      if (abortControllerRef.current === controller) {
        setIsLoading(false);
        abortControllerRef.current = null;
      }
    }
  }, [
    authorizedFetch,
    baseUrl,
    preFireDate,
    postFireDate,
    areaOfInterest,
    severityDistribution,
    isLoading,
  ]);

  // Start analysis when modal opens
  useEffect(() => {
    if (isModalOpen && !analysisText && !isLoading && !error) {
      startAnalysis();
    }
  }, [isModalOpen, analysisText, isLoading, error, startAnalysis]);

  if (!isVisible) {
    return null;
  }

  return (
    <>
      {/* Floating Action Button */}
      <button
        type="button"
        className="ai-analysis-fab"
        onClick={openModal}
        title="AI Analysis"
        aria-label="Open AI Analysis"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="24"
          height="24"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M12 2a2 2 0 0 1 2 2c0 .74-.4 1.39-1 1.73V7h1a7 7 0 0 1 7 7h1a2 2 0 0 1 0 4h-1v1a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-1H2a2 2 0 0 1 0-4h1a7 7 0 0 1 7-7h1V5.73c-.6-.34-1-.99-1-1.73a2 2 0 0 1 2-2z" />
          <circle cx="7.5" cy="14.5" r="1.5" />
          <circle cx="16.5" cy="14.5" r="1.5" />
        </svg>
      </button>

      {/* Modal */}
      {isModalOpen && (
        <div className="ai-analysis-modal-backdrop" onClick={closeModal}>
          <div
            className="ai-analysis-modal"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="ai-analysis-modal-header">
              <h2 className="ai-analysis-modal-title">
                🤖 AI Wildfire Analysis
              </h2>
              <button
                type="button"
                className="ai-analysis-modal-close"
                onClick={closeModal}
                aria-label="Close"
              >
                ×
              </button>
            </div>

            <div className="ai-analysis-modal-body" ref={contentRef}>
              {error && (
                <div className="alert alert-danger" role="alert">
                  {error}
                  <button
                    type="button"
                    className="btn btn-outline-danger btn-sm ms-3"
                    onClick={startAnalysis}
                  >
                    Retry
                  </button>
                </div>
              )}

              {!error && !analysisText && isLoading && (
                <div className="text-center py-5">
                  <div className="spinner-border text-primary mb-3" role="status">
                    <span className="visually-hidden">Loading...</span>
                  </div>
                  <p className="text-muted">Generating AI analysis...</p>
                </div>
              )}

              {analysisText && (
                <div className="ai-analysis-content">
                  <ReactMarkdown>{analysisText}</ReactMarkdown>
                  {isLoading && (
                    <span className="ai-analysis-cursor">▌</span>
                  )}
                </div>
              )}
            </div>

            <div className="ai-analysis-modal-footer">
              <small className="text-muted">
                Powered by OpenAI GPT-4o-mini
              </small>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={closeModal}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

export default AIAnalysisModal;
