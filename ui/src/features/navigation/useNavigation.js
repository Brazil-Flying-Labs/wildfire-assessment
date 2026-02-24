import { useCallback, useEffect, useRef, useState } from "react";
import { faro } from "../../config/faroConfig";

export default function useNavigation({ onNavigateTo, onPopState } = {}) {
  const [currentPage, setCurrentPage] = useState("dashboard");
  const [selectedAnalysisId, setSelectedAnalysisId] = useState(null);
  const [scrollToDeliverable, setScrollToDeliverable] = useState(null);

  // Use refs so callbacks have stable identity
  const onNavigateToRef = useRef(onNavigateTo);
  const onPopStateRef = useRef(onPopState);
  useEffect(() => {
    onNavigateToRef.current = onNavigateTo;
    onPopStateRef.current = onPopState;
  });

  const navigateTo = useCallback((page, { replace = false } = {}) => {
    setCurrentPage(page);
    setSelectedAnalysisId(null);
    if (onNavigateToRef.current) onNavigateToRef.current();
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

  const goBack = useCallback(() => {
    window.history.back();
  }, []);

  // Handle browser back/forward buttons
  useEffect(() => {
    const handlePopState = (event) => {
      const state = event.state;
      if (!state) {
        window.history.pushState(
          { page: "dashboard", analysisId: null, landing: false },
          ""
        );
        return;
      }
      setCurrentPage(state.page || "dashboard");
      setSelectedAnalysisId(state.analysisId || null);
      if (onPopStateRef.current) onPopStateRef.current();
      if (faro) faro.api.setView({ name: state.page || "dashboard" });
    };

    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  return {
    currentPage,
    selectedAnalysisId,
    scrollToDeliverable,
    navigateTo,
    handleAnalysisClick,
    goBack,
  };
}
