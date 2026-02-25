import { useCallback, useEffect, useRef, useState } from "react";
import { faro } from "../../config/faroConfig";
import { posthog } from "../../config/posthogConfig";

const PAGE_PATHS = {
  dashboard: "/dashboard",
  analysis: "/analysis",
  areas: "/areas",
  profile: "/profile",
  "analysis-detail": "/analysis-detail",
};

const PATH_TO_PAGE = Object.fromEntries(
  Object.entries(PAGE_PATHS).map(([page, path]) => [path, page])
);

function pageFromPathname() {
  return PATH_TO_PAGE[window.location.pathname] || null;
}

export default function useNavigation({ onNavigateTo, onPopState } = {}) {
  // Initialize state from URL pathname first, then history state, then default
  const [currentPage, setCurrentPage] = useState(() => {
    return pageFromPathname() || window.history.state?.page || "dashboard";
  });
  const [selectedAnalysisId, setSelectedAnalysisId] = useState(() => {
    return window.history.state?.analysisId || null;
  });
  const [scrollToDeliverable, setScrollToDeliverable] = useState(null);

  // Sync initial URL on mount (replace state so URL matches)
  useEffect(() => {
    const path = PAGE_PATHS[currentPage] || "/dashboard";
    if (window.location.pathname !== path) {
      window.history.replaceState(
        { page: currentPage, analysisId: selectedAnalysisId, landing: false },
        "",
        path
      );
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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
    const path = PAGE_PATHS[page] || "/dashboard";
    if (replace) {
      window.history.replaceState(state, "", path);
    } else {
      window.history.pushState(state, "", path);
    }
    if (faro) faro.api.setView({ name: page });
    if (posthog) posthog.capture("$pageview", { page });
  }, []);

  const handleAnalysisClick = useCallback((analysisId, deliverableName) => {
    setSelectedAnalysisId(analysisId);
    setScrollToDeliverable(deliverableName || null);
    setCurrentPage("analysis-detail");
    window.history.pushState(
      { page: "analysis-detail", analysisId, landing: false },
      "",
      PAGE_PATHS["analysis-detail"]
    );
    if (faro) faro.api.setView({ name: "analysis-detail" });
    if (posthog) posthog.capture("$pageview", { page: "analysis-detail" });
  }, []);

  const goBack = useCallback(() => {
    window.history.back();
  }, []);

  // Handle browser back/forward buttons
  useEffect(() => {
    const handlePopState = (event) => {
      const state = event.state;
      if (!state) {
        const page = pageFromPathname() || "dashboard";
        setCurrentPage(page);
        setSelectedAnalysisId(null);
        window.history.replaceState(
          { page, analysisId: null, landing: false },
          "",
          PAGE_PATHS[page] || "/dashboard"
        );
        if (faro) faro.api.setView({ name: page });
        if (posthog) posthog.capture("$pageview", { page });
        return;
      }
      setCurrentPage(state.page || "dashboard");
      setSelectedAnalysisId(state.analysisId || null);
      if (onPopStateRef.current) onPopStateRef.current();
      if (faro) faro.api.setView({ name: state.page || "dashboard" });
      if (posthog) posthog.capture("$pageview", { page: state.page || "dashboard" });
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
