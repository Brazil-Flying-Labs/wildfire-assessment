import { useCallback, useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import { useLanguage } from "../../context/LanguageContext";

const RESPONSE_ID_REGEX = /\n?\n?\[RESPONSE_ID\](.*?)\[\/RESPONSE_ID\]/;

/**
 * Parse streaming text to extract the response_id marker.
 */
function extractMarkers(text) {
  let responseId = null;
  const idMatch = text.match(RESPONSE_ID_REGEX);
  if (idMatch) {
    responseId = idMatch[1];
    text = text.replace(RESPONSE_ID_REGEX, "");
  }
  return { text, responseId };
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
  polygonPath,
  authorizedFetch,
  baseUrl,
}) {
  const { t } = useLanguage();
  const [isModalOpen, setIsModalOpen] = useState(false);
  // messages: [{ role: "assistant"|"user", text: string }]
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [question, setQuestion] = useState("");
  const [aiProvider, setAiProvider] = useState(null);
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

    setIsModalOpen(false);
    responseIdRef.current = null;
  }, [preFireDate, postFireDate, areaOfInterest, severityDistribution]);

  // Track whether user is scrolled to the bottom
  const [showScrollDown, setShowScrollDown] = useState(false);

  useEffect(() => {
    const el = contentRef.current;
    if (!el) return;
    const handleScroll = () => {
      const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 40;
      setShowScrollDown(!nearBottom);
    };
    el.addEventListener("scroll", handleScroll);
    return () => el.removeEventListener("scroll", handleScroll);
  }, [isModalOpen]);

  // Update arrow visibility when content grows during streaming
  useEffect(() => {
    const el = contentRef.current;
    if (!el) return;
    const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 40;
    setShowScrollDown(!nearBottom);
  }, [messages]);

  const scrollToBottom = useCallback(() => {
    if (contentRef.current) {
      contentRef.current.scrollTo({ top: contentRef.current.scrollHeight, behavior: "smooth" });
    }
  }, []);

  const openModal = useCallback(() => {
    setIsModalOpen(true);
  }, []);

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
    // Read provider from header immediately so it displays while streaming
    const headerProvider = response.headers.get("X-AI-Provider");
    if (headerProvider) {
      setAiProvider(headerProvider);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let fullText = "";
    let isFirstChunk = true;

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const chunk = decoder.decode(value, { stream: true });
      fullText += chunk;

      // Scroll to show the beginning of the response on first chunk
      if (isFirstChunk) {
        isFirstChunk = false;
        setTimeout(scrollToBottom, 50);
      }

      // Strip markers for display
      const { text: cleanText } = extractMarkers(fullText);
      setMessages((prev) => {
        const updated = [...prev];
        updated[updated.length - 1] = { role: "assistant", text: cleanText };
        return updated;
      });
    }

    const { text: finalText, responseId } = extractMarkers(fullText);
    if (responseId) {
      responseIdRef.current = responseId;
    }
    setMessages((prev) => {
      const updated = [...prev];
      updated[updated.length - 1] = { role: "assistant", text: finalText };
      return updated;
    });
  }, [scrollToBottom]);

  const startAnalysis = useCallback(async (userQuestion = "") => {
    if (!baseUrl || isLoading) return;

    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    const controller = new AbortController();
    abortControllerRef.current = controller;

    setIsLoading(true);
    setMessages((prev) => [
      ...prev,
      ...(userQuestion ? [{ role: "user", text: userQuestion }] : []),
      { role: "assistant", text: "" },
    ]);

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
          polygon_path: polygonPath || "",
          question: userQuestion,
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

      // Replace the empty assistant placeholder with the error message
      setMessages((prev) => [
        ...prev.slice(0, -1),
        { role: "assistant", text: t("ai.errorMessage"), isError: true },
      ]);
    } finally {
      if (abortControllerRef.current === controller) {
        setIsLoading(false);
        abortControllerRef.current = null;
      }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authorizedFetch, baseUrl, preFireDate, postFireDate, areaOfInterest, readStream, t]);

  const sendFollowUp = useCallback(async () => {
    const trimmed = question.trim();
    if (!trimmed || !baseUrl || isLoading) return;

    // First question of a fresh chat: run the full analysis with the
    // question embedded in the prompt instead of a follow-up.
    if (!responseIdRef.current) {
      setQuestion("");
      await startAnalysis(trimmed);
      return;
    }

    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    const controller = new AbortController();
    abortControllerRef.current = controller;

    setQuestion("");
    setIsLoading(true);

    setMessages((prev) => [
      ...prev,
      { role: "user", text: trimmed },
      { role: "assistant", text: "" },
    ]);
    // Scroll so the user sees their message
    setTimeout(scrollToBottom, 50);

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

      // Replace the empty assistant placeholder with the error message
      setMessages((prev) => [
        ...prev.slice(0, -1),
        { role: "assistant", text: t("ai.errorMessage"), isError: true },
      ]);
    } finally {
      if (abortControllerRef.current === controller) {
        setIsLoading(false);
        abortControllerRef.current = null;
      }
    }
  }, [authorizedFetch, baseUrl, isLoading, question, readStream, scrollToBottom, startAnalysis, t]);

  const retryLast = useCallback(async () => {
    if (!baseUrl || isLoading) return;

    // Find the last user message before the error to determine what to retry
    const lastUserMsg = [...messages].reverse().find((m) => m.role === "user");
    if (!lastUserMsg) {
      // No user message — retry initial analysis
      startAnalysis();
      return;
    }

    // Retry the last follow-up: remove error message, add empty assistant placeholder
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const controller = new AbortController();
    abortControllerRef.current = controller;

    setIsLoading(true);

    setMessages((prev) => {
      // Remove the error assistant message, keep everything else including user msg
      const withoutError = prev.filter((m) => !m.isError);
      return [...withoutError, { role: "assistant", text: "" }];
    });
    setTimeout(scrollToBottom, 50);

    try {
      const response = await authorizedFetch(`${baseUrl}/analysis/followup/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          previous_response_id: responseIdRef.current,
          question: lastUserMsg.text,
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
      console.error("AI Follow-up retry error:", err);

      setMessages((prev) => [
        ...prev.slice(0, -1),
        { role: "assistant", text: t("ai.errorMessage"), isError: true },
      ]);
    } finally {
      if (abortControllerRef.current === controller) {
        setIsLoading(false);
        abortControllerRef.current = null;
      }
    }
  }, [authorizedFetch, baseUrl, isLoading, messages, readStream, scrollToBottom, startAnalysis, t]);

  const handleKeyDown = useCallback(
    (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendFollowUp();
      }
    },
    [sendFollowUp]
  );

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
        title={t("ai.openAnalysis")}
        aria-label={t("ai.openAnalysis")}
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
                {t("ai.title")}
              </h2>
              <button
                type="button"
                className="ai-analysis-modal-close"
                onClick={closeModal}
                aria-label={t("common.close")}
              >
                &times;
              </button>
            </div>

            <div className="ai-analysis-modal-body" ref={contentRef}>
              {!messages.length && isLoading && (
                <div className="text-center py-5">
                  <div className="spinner-border text-primary mb-3" role="status">
                    <span className="visually-hidden">{t("common.loading")}</span>
                  </div>
                  <p className="text-muted">{t("ai.generating")}</p>
                </div>
              )}

              {messages.map((msg, idx) => (
                <div
                  key={idx}
                  className={`ai-chat-message ai-chat-${msg.role}`}
                >
                  {msg.role === "user" ? (
                    <div className="ai-chat-user-bubble">{msg.text}</div>
                  ) : msg.isError ? (
                    <div className="ai-chat-error-bubble">
                      <p>{msg.text}</p>
                      <button
                        type="button"
                        className="btn btn-outline-danger btn-sm"
                        onClick={retryLast}
                      >
                        {t("ai.retry")}
                      </button>
                    </div>
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

              {showScrollDown && (
                <button
                  type="button"
                  className="ai-scroll-down-btn"
                  onClick={scrollToBottom}
                  aria-label={t("ai.scrollToBottom")}
                >
                  <svg
                    width="18"
                    height="18"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <polyline points="6 9 12 15 18 9" />
                  </svg>
                </button>
              )}
            </div>

            <div className="ai-analysis-modal-footer">
              <div className="ai-chat-input-row">
                <input
                  ref={inputRef}
                  type="text"
                  className="form-control form-control-sm"
                  placeholder={
                    responseIdRef.current
                      ? t("ai.followUpPlaceholder")
                      : t("ai.firstQuestionPlaceholder")
                  }
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
                  {t("ai.send")}
                </button>
              </div>
              <div className="ai-chat-footer-meta">
                {aiProvider && (
                  <small className="text-muted">
                    {t("ai.poweredBy").replace("{provider}", aiProvider)}
                  </small>
                )}
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={closeModal}
                >
                  {t("common.close")}
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
