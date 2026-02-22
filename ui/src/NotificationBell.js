import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { useLanguage } from "./LanguageContext";

function NotificationBell({
  onNotificationClick,
  unreadCount,
  notifications,
  onOpen,
  loading,
  hasMore,
  onLoadMore,
  onMarkAllRead,
}) {
  const { t } = useLanguage();
  const [isOpen, setIsOpen] = useState(false);
  const [position, setPosition] = useState(null);
  const triggerRef = useRef(null);
  const dropdownRef = useRef(null);
  const bodyRef = useRef(null);

  const toggle = useCallback(() => {
    const willOpen = !isOpen;
    setIsOpen(willOpen);
    if (willOpen) {
      // Calculate position from the trigger button
      if (triggerRef.current) {
        const rect = triggerRef.current.getBoundingClientRect();
        setPosition({ top: rect.bottom + 6, right: window.innerWidth - rect.right });
      }
      if (onOpen) onOpen();
    }
  }, [isOpen, onOpen]);

  // Lock body scroll while dropdown is open on mobile
  useEffect(() => {
    if (!isOpen || window.innerWidth >= 768) return;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = "";
    };
  }, [isOpen]);

  // Close on outside click (check both the trigger button and the portal dropdown)
  useEffect(() => {
    if (!isOpen) return;
    const handleClick = (e) => {
      const inTrigger =
        triggerRef.current && triggerRef.current.contains(e.target);
      const inDropdown =
        dropdownRef.current && dropdownRef.current.contains(e.target);
      if (!inTrigger && !inDropdown) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [isOpen]);

  // Infinite scroll
  useEffect(() => {
    const body = bodyRef.current;
    if (!body || !isOpen) return;
    const handleScroll = () => {
      const { scrollTop, scrollHeight, clientHeight } = body;
      if (scrollHeight - scrollTop - clientHeight < 50 && hasMore && !loading) {
        onLoadMore();
      }
    };
    body.addEventListener("scroll", handleScroll);
    return () => body.removeEventListener("scroll", handleScroll);
  }, [isOpen, hasMore, loading, onLoadMore]);

  const handleNotificationClick = useCallback(
    (notification) => {
      setIsOpen(false);
      if (notification.analysis_run_id && onNotificationClick) {
        onNotificationClick(
          notification.analysis_run_id,
          notification.deliverable_name
        );
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

  // Group consecutive notifications by area_name so nearby deliverables
  // from the same area collapse into a single visual block.
  const groupedNotifications = useMemo(() => {
    const groups = [];
    for (const n of notifications) {
      const last = groups[groups.length - 1];
      if (last && last.area_name === n.area_name) {
        last.items.push(n);
        if (!n.is_read) last.hasUnread = true;
      } else {
        groups.push({
          area_name: n.area_name,
          items: [n],
          hasUnread: !n.is_read,
        });
      }
    }
    return groups;
  }, [notifications]);

  // Inline positioning for desktop (portal); mobile overrides via CSS
  const dropdownStyle = position
    ? { top: position.top, right: position.right }
    : {};

  const dropdown = isOpen && (
    <div
      className="notification-dropdown"
      ref={dropdownRef}
      style={dropdownStyle}
    >
      <div className="notification-dropdown-header">
        <span className="fw-semibold">{t("notifications.title")}</span>
        {unreadCount > 0 && onMarkAllRead && (
          <button
            type="button"
            className="notification-mark-all-read"
            onClick={onMarkAllRead}
          >
            {t("notifications.markAllRead")}
          </button>
        )}
      </div>
      <div className="notification-dropdown-body" ref={bodyRef}>
        {loading && notifications.length === 0 ? (
          <div className="notification-empty">
            <div
              className="spinner-border spinner-border-sm text-primary"
              role="status"
            >
              <span className="visually-hidden">
                {t("common.loading")}
              </span>
            </div>
          </div>
        ) : notifications.length === 0 ? (
          <div className="notification-empty">
            {t("notifications.empty")}
          </div>
        ) : (
          <>
            {groupedNotifications.map((group, gi) => (
              group.items.length === 1 ? (
                <button
                  key={group.items[0].id}
                  type="button"
                  className={`notification-item${group.items[0].is_read ? "" : " is-unread"}`}
                  onClick={() => handleNotificationClick(group.items[0])}
                >
                  <div className="notification-item-text">
                    {t("notifications.deliverableReady", {
                      deliverable: group.items[0].deliverable_name,
                      area: group.items[0].area_name,
                    })}
                  </div>
                  <div className="notification-item-time">
                    {formatTimeAgo(group.items[0].created_at)}
                  </div>
                </button>
              ) : (
                <div key={`group-${gi}`} className={`notification-group${group.hasUnread ? " is-unread" : ""}`}>
                  <div className="notification-group-header">
                    <span className="notification-group-area">{group.area_name}</span>
                    <span className="notification-group-count">
                      {t("notifications.groupCount", { count: group.items.length })}
                    </span>
                  </div>
                  {group.items.map((n) => (
                    <button
                      key={n.id}
                      type="button"
                      className={`notification-item notification-item--grouped${n.is_read ? "" : " is-unread"}`}
                      onClick={() => handleNotificationClick(n)}
                    >
                      <div className="notification-item-text">
                        {n.deliverable_name}
                      </div>
                      <div className="notification-item-time">
                        {formatTimeAgo(n.created_at)}
                      </div>
                    </button>
                  ))}
                </div>
              )
            ))}
            {loading && (
              <div className="notification-empty">
                <div
                  className="spinner-border spinner-border-sm text-primary"
                  role="status"
                >
                  <span className="visually-hidden">
                    {t("common.loading")}
                  </span>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );

  return (
    <div className="notification-bell" ref={triggerRef}>
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
      {createPortal(dropdown, document.body)}
    </div>
  );
}

export default NotificationBell;
