import { useCallback, useEffect, useRef, useState } from "react";
import { useLanguage } from "./LanguageContext";

function NotificationBell({
  onNotificationClick,
  unreadCount,
  notifications,
  onOpen,
}) {
  const { t } = useLanguage();
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef(null);

  const toggle = useCallback(() => {
    const willOpen = !isOpen;
    setIsOpen(willOpen);
    if (willOpen && onOpen) onOpen();
  }, [isOpen, onOpen]);

  // Close on outside click
  useEffect(() => {
    if (!isOpen) return;
    const handleClick = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [isOpen]);

  const handleNotificationClick = useCallback(
    (notification) => {
      setIsOpen(false);
      if (notification.analysis_run_id && onNotificationClick) {
        onNotificationClick(notification.analysis_run_id);
      }
    },
    [onNotificationClick]
  );

  const formatTimeAgo = useCallback(
    (dateString) => {
      const date = new Date(dateString);
      const now = new Date();
      const diffMs = now - date;
      const diffMins = Math.floor(diffMs / 60000);
      if (diffMins < 1) return t("notifications.justNow");
      if (diffMins < 60)
        return t("notifications.minutesAgo", { count: diffMins });
      const diffHours = Math.floor(diffMins / 60);
      if (diffHours < 24)
        return t("notifications.hoursAgo", { count: diffHours });
      const diffDays = Math.floor(diffHours / 24);
      return t("notifications.daysAgo", { count: diffDays });
    },
    [t]
  );

  return (
    <div className="notification-bell" ref={menuRef}>
      <button
        type="button"
        className="notification-bell-trigger"
        onClick={toggle}
        aria-label={t("notifications.title")}
      >
        <svg
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
          <path d="M13.73 21a2 2 0 0 1-3.46 0" />
        </svg>
        {unreadCount > 0 && (
          <span className="notification-badge">
            {unreadCount > 99 ? "99+" : unreadCount}
          </span>
        )}
      </button>
      {isOpen && (
        <div className="notification-dropdown">
          <div className="notification-dropdown-header">
            <span className="fw-semibold">{t("notifications.title")}</span>
          </div>
          <div className="notification-dropdown-body">
            {notifications.length === 0 ? (
              <div className="notification-empty">
                {t("notifications.empty")}
              </div>
            ) : (
              notifications.map((n) => (
                <button
                  key={n.id}
                  type="button"
                  className={`notification-item${n.is_read ? "" : " is-unread"}`}
                  onClick={() => handleNotificationClick(n)}
                >
                  <div className="notification-item-text">
                    {t("notifications.deliverableReady", {
                      deliverable: n.deliverable_name,
                      area: n.area_name,
                    })}
                  </div>
                  <div className="notification-item-time">
                    {formatTimeAgo(n.created_at)}
                  </div>
                </button>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default NotificationBell;
