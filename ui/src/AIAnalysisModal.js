import { useCallback, useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";

const RESPONSE_ID_REGEX = /\n?\n?\[RESPONSE_ID\](.*?)\[\/RESPONSE_ID\]$/;

/**
 * Parse streaming text to extract the response_id marker appended by the backend.
 */
function extractResponseId(text) {
  const match = text.match(RESPONSE_ID_REGEX);
  if (match) {
    return { text: text.replace(RESPONSE_ID_REGEX, ""), responseId: match[1] };
  }
  return { text, responseId: null };
}

/**
 * AI Analysis floating button and modal component with follow-up chat.
 * Only visible for authorized test users.
 */
function AIAnalysisModal({
  isVisible,
  preFireDate,
  postFireDate,
  areaOfInterest,
  severityDistribution,
  imageUrls,
  authorizedFetch,
  baseUrl,
}) {
  const [isModalOpen, setIsModalOpen] = useState(false);
  // messages: [{ role: "assistant"|"user", text: string }]
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [question, setQuestion] = useState("");
  const responseIdRef = useRef(null);
  const abortControllerRef = useRef(null);
  const contentRef = useRef(null);
  const inputRef = useRef(null);
  const severityRef = useRef(severityDistribution);
  const imageUrlsRef = useRef(imageUrls);
  severityRef.current = severityDistribution;
  imageUrlsRef.current = imageUrls;

  // Clear cached AI analysis when a new fire analysis is run
  useEffect(() => {
    setMessages([]);
    setError(null);
    setIsModalOpen(false);
    responseIdRef.current = null;
  }, [preFireDate, postFireDate, areaOfInterest, severityDistribution]);

  // Auto-scroll to bottom as content changes
  useEffect(() => {
    if (contentRef.current) {
      contentRef.current.scrollTop = contentRef.current.scrollHeight;
    }
  }, [messages, isLoading]);

  const startAnalysisRef = useRef(null);

  const openModal = useCallback(() => {
    setIsModalOpen(true);
    if (!messages.length && !isLoading) {
      setError(null);
      startAnalysisRef.current = true;
    }
  }, [messages.length, isLoading]);

  const closeModal = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsModalOpen(false);
    setIsLoading(false);
  }, []);

  /**
   * Read a streaming response, appending text to the last assistant message.
   * Extracts the response_id from the final marker.
   */
  const readStream = useCallback(async (response) => {
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let fullText = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const chunk = decoder.decode(value, { stream: true });
      fullText += chunk;

      // Strip the response_id marker for display
      const { text: cleanText } = extractResponseId(fullText);
      setMessages((prev) => {
        const updated = [...prev];
        updated[updated.length - 1] = { role: "assistant", text: cleanText };
        return updated;
      });
    }

    const { text: finalText, responseId } = extractResponseId(fullText);
    if (responseId) {
      responseIdRef.current = responseId;
    }
    setMessages((prev) => {
      const updated = [...prev];
      updated[updated.length - 1] = { role: "assistant", text: finalText };
      return updated;
    });
  }, []);

  const startAnalysis = useCallback(async () => {
    if (!baseUrl || isLoading) return;

    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    const controller = new AbortController();
    abortControllerRef.current = controller;

    setIsLoading(true);
    setMessages([{ role: "assistant", text: "" }]);
    setError(null);
    responseIdRef.current = null;

    try {
      const images = imageUrlsRef.current || [];
      const imageDataUrls = await Promise.all(
        images.map(async ({ label, url }) => {
          try {
            const resp = await fetch(url);
            const blob = await resp.blob();
            const dataUrl = await new Promise((resolve) => {
              const reader = new FileReader();
              reader.onloadend = () => resolve(reader.result);
              reader.readAsDataURL(blob);
            });
            return { label, url: dataUrl };
          } catch {
            return null;
          }
        })
      );

      const response = await authorizedFetch(`${baseUrl}/analysis/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          pre_fire_date: preFireDate,
          post_fire_date: postFireDate,
          area_of_interest: areaOfInterest,
          severity_distribution: severityRef.current,
          image_urls: imageDataUrls.filter(Boolean),

        }),
        signal: controller.signal,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || `HTTP ${response.status}`);
      }

      await readStream(response);
    } catch (err) {
      if (err.name === "AbortError") return;
      console.error("AI Analysis error:", err);
      setError(err.message || "Failed to generate analysis");
      setMessages([]);
    } finally {
      if (abortControllerRef.current === controller) {
        setIsLoading(false);
        abortControllerRef.current = null;
      }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authorizedFetch, baseUrl, preFireDate, postFireDate, areaOfInterest, readStream]);

  const sendFollowUp = useCallback(async () => {
    const trimmed = question.trim();
    if (!trimmed || !baseUrl || isLoading || !responseIdRef.current) return;

    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    const controller = new AbortController();
    abortControllerRef.current = controller;

    setQuestion("");
    setIsLoading(true);
    setError(null);
    setMessages((prev) => [
      ...prev,
      { role: "user", text: trimmed },
      { role: "assistant", text: "" },
    ]);

    try {
      const response = await authorizedFetch(`${baseUrl}/analysis/followup/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          previous_response_id: responseIdRef.current,
          question: trimmed,

        }),
        signal: controller.signal,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || `HTTP ${response.status}`);
      }

      await readStream(response);
    } catch (err) {
      if (err.name === "AbortError") return;
      console.error("AI Follow-up error:", err);
      setError(err.message || "Failed to get response");
      // Remove the empty assistant message
      setMessages((prev) => prev.slice(0, -1));
    } finally {
      if (abortControllerRef.current === controller) {
        setIsLoading(false);
        abortControllerRef.current = null;
      }
    }
  }, [authorizedFetch, baseUrl, isLoading, question, readStream]);

  const handleKeyDown = useCallback(
    (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendFollowUp();
      }
    },
    [sendFollowUp]
  );

  // Start analysis once when modal opens
  useEffect(() => {
    if (startAnalysisRef.current && isModalOpen) {
      startAnalysisRef.current = false;
      startAnalysis();
    }
  }, [isModalOpen, startAnalysis]);

  // Focus input when loading finishes and there are messages
  useEffect(() => {
    if (!isLoading && messages.length > 0 && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isLoading, messages.length]);

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
                AI Wildfire Analysis
              </h2>
              <button
                type="button"
                className="ai-analysis-modal-close"
                onClick={closeModal}
                aria-label="Close"
              >
                &times;
              </button>
            </div>

            <div className="ai-analysis-modal-body" ref={contentRef}>
              {error && (
                <div className="alert alert-danger" role="alert">
                  {error}
                  <button
                    type="button"
                    className="btn btn-outline-danger btn-sm ms-3"
                    onClick={messages.length ? sendFollowUp : startAnalysis}
                  >
                    Retry
                  </button>
                </div>
              )}

              {!error && !messages.length && isLoading && (
                <div className="text-center py-5">
                  <div className="spinner-border text-primary mb-3" role="status">
                    <span className="visually-hidden">Loading...</span>
                  </div>
                  <p className="text-muted">Generating AI analysis...</p>
                </div>
              )}

              {messages.map((msg, idx) => (
                <div
                  key={idx}
                  className={`ai-chat-message ai-chat-${msg.role}`}
                >
                  {msg.role === "user" ? (
                    <div className="ai-chat-user-bubble">{msg.text}</div>
                  ) : (
                    <div className="ai-analysis-content">
                      <ReactMarkdown>{msg.text}</ReactMarkdown>
                      {isLoading && idx === messages.length - 1 && (
                        <span className="ai-analysis-cursor">&#9612;</span>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>

            <div className="ai-analysis-modal-footer">
              {messages.length > 0 && responseIdRef.current && (
                <div className="ai-chat-input-row">
                  <input
                    ref={inputRef}
                    type="text"
                    className="form-control form-control-sm"
                    placeholder="Ask a follow-up question..."
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    onKeyDown={handleKeyDown}
                    disabled={isLoading}
                  />
                  <button
                    type="button"
                    className="btn btn-primary btn-sm"
                    onClick={sendFollowUp}
                    disabled={isLoading || !question.trim()}
                  >
                    Send
                  </button>
                </div>
              )}
              <div className="ai-chat-footer-meta">
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
        </div>
      )}
    </>
  );
}

export default AIAnalysisModal;
