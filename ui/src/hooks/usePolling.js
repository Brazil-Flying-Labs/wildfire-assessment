import { useCallback, useEffect, useRef } from "react";

export default function usePolling() {
  const intervalsRef = useRef({});

  const startPolling = useCallback((key, pollFn, intervalMs = 5000) => {
    if (intervalsRef.current[key]) {
      clearInterval(intervalsRef.current[key]);
    }

    const intervalId = setInterval(pollFn, intervalMs);
    intervalsRef.current[key] = intervalId;

    return () => {
      clearInterval(intervalId);
      delete intervalsRef.current[key];
    };
  }, []);

  const stopPolling = useCallback((key) => {
    if (intervalsRef.current[key]) {
      clearInterval(intervalsRef.current[key]);
      delete intervalsRef.current[key];
    }
  }, []);

  const stopAll = useCallback(() => {
    Object.values(intervalsRef.current).forEach(clearInterval);
    intervalsRef.current = {};
  }, []);

  useEffect(() => {
    const intervals = intervalsRef.current;
    return () => {
      Object.values(intervals).forEach(clearInterval);
    };
  }, []);

  return { startPolling, stopPolling, stopAll };
}
