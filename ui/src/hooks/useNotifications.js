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
          // One chime per newly-ready deliverable, staggered so a batch
          // of simultaneous completions is still distinguishable.
          const delta = newCount - prevUnreadRef.current;
          for (let i = 0; i < delta; i += 1) {
            setTimeout(playNotificationSound, i * 350);
          }
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

  const markRead = useCallback(
    (notificationId) => {
      if (!baseUrl || !notificationId) return;
      // Optimistically update local state
      setNotifications((prev) =>
        prev.map((n) => (n.id === notificationId ? { ...n, is_read: true } : n))
      );
      // Persist on server and sync polled count
      authorizedFetch(`${baseUrl}/notifications/${notificationId}/read/`, {
        method: "PATCH",
      })
        .then((res) => {
          if (res.ok) {
            prevUnreadRef.current = null;
            fetchUnreadCount();
          }
        })
        .catch(() => {});
    },
    [authorizedFetch, baseUrl, fetchUnreadCount]
  );

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

  // Fetch notifications + poll unread count every 5 seconds
  useEffect(() => {
    if (!authReady || !baseUrl) return;
    fetchUnreadCount();
    fetchNotifications();
    pollRef.current = setInterval(fetchUnreadCount, 5000);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [authReady, baseUrl, fetchUnreadCount, fetchNotifications]);

  // Badge count = number of unread notifications (each deliverable counts).
  const unreadFromList = notifications.filter((n) => !n.is_read).length;

  // Use the loaded list when available, otherwise fall back to the
  // polled unreadCount so the badge shows something before the list loads.
  const badgeCount = notifications.length > 0 ? unreadFromList : unreadCount;

  return {
    notifications,
    unreadCount: badgeCount,
    loading,
    hasMore: !!nextUrl,
    fetchNotifications,
    fetchMore,
    markAllRead,
    markRead,
    fetchUnreadCount,
  };
}
