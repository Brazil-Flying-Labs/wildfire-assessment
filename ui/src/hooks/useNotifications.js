import { useCallback, useEffect, useRef, useState } from "react";

function playNotificationSound() {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.type = "sine";
    // Two-tone chime
    osc.frequency.setValueAtTime(880, ctx.currentTime);
    osc.frequency.setValueAtTime(1174.66, ctx.currentTime + 0.1);
    gain.gain.setValueAtTime(0.3, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.3);
    osc.start(ctx.currentTime);
    osc.stop(ctx.currentTime + 0.3);
  } catch {
    // Audio not available
  }
}

export default function useNotifications(authorizedFetch, baseUrl, authReady) {
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [nextUrl, setNextUrl] = useState(null);
  const pollRef = useRef(null);
  const prevUnreadRef = useRef(null);

  const fetchUnreadCount = useCallback(async () => {
    if (!baseUrl) return;
    try {
      const response = await authorizedFetch(
        `${baseUrl}/notifications/unread_count/`
      );
      if (response.ok) {
        const data = await response.json();
        const newCount = data.unread_count;
        if (prevUnreadRef.current !== null && newCount > prevUnreadRef.current) {
          playNotificationSound();
        }
        prevUnreadRef.current = newCount;
        setUnreadCount(newCount);
      }
    } catch {
      // Silently ignore polling errors
    }
  }, [authorizedFetch, baseUrl]);

  const fetchNotifications = useCallback(
    async (url) => {
      if (!baseUrl) return;
      const fetchUrl = url || `${baseUrl}/notifications/`;
      setLoading(true);
      try {
        const response = await authorizedFetch(fetchUrl);
        if (response.ok) {
          const data = await response.json();
          setNotifications((prev) =>
            url ? [...prev, ...(data.results || [])] : data.results || []
          );
          setNextUrl(data.next);
        }
      } catch {
        // Silently ignore
      } finally {
        setLoading(false);
      }
    },
    [authorizedFetch, baseUrl]
  );

  const fetchMore = useCallback(() => {
    if (nextUrl && !loading) {
      fetchNotifications(nextUrl);
    }
  }, [nextUrl, loading, fetchNotifications]);

  const markAllRead = useCallback(async () => {
    if (!baseUrl) return;
    try {
      const response = await authorizedFetch(
        `${baseUrl}/notifications/mark-all-read/`,
        { method: "POST" }
      );
      if (response.ok) {
        setNotifications((prev) =>
          prev.map((n) => ({ ...n, is_read: true }))
        );
        setUnreadCount(0);
        prevUnreadRef.current = 0;
      }
    } catch {
      // Silently ignore
    }
  }, [authorizedFetch, baseUrl]);

  // Poll for unread notification count every 5 seconds
  useEffect(() => {
    if (!authReady || !baseUrl) return;
    fetchUnreadCount();
    pollRef.current = setInterval(fetchUnreadCount, 5000);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [authReady, baseUrl, fetchUnreadCount]);

  return {
    notifications,
    unreadCount,
    loading,
    hasMore: !!nextUrl,
    fetchNotifications,
    fetchMore,
    markAllRead,
    fetchUnreadCount,
  };
}
