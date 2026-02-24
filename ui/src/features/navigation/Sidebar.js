function Sidebar({
  isOpen,
  isPinned,
  isCollapsing,
  currentPage,
  navigateTo,
  onClose,
  onTogglePin,
  onCollapsingEnd,
  user,
  displayName,
  logout,
  t,
}) {
  return (
    <>
      {isOpen && (
        <button
          type="button"
          className="nav-backdrop"
          onClick={onClose}
          aria-label={t("common.close")}
        >
          <span className="visually-hidden">{t("common.close")}</span>
        </button>
      )}
      <nav
        className={`nav-sidebar ${isPinned ? "is-pinned" : ""} ${isCollapsing ? "is-collapsing" : ""} ${isOpen ? "is-open" : ""}`}
        onMouseLeave={() => isCollapsing && onCollapsingEnd()}
      >
        <div className="nav-sidebar-header d-flex justify-content-end align-items-center p-3">
          <button
            type="button"
            className="btn btn-link text-dark p-0"
            onClick={onClose}
            aria-label={t("common.close")}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>
        <ul className="nav-sidebar-menu list-unstyled m-0 p-0">
          <li>
            <button
              type="button"
              className={`nav-sidebar-item ${currentPage === "dashboard" ? "active" : ""}`}
              onClick={() => navigateTo("dashboard")}
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="3" y="3" width="7" height="7" />
                <rect x="14" y="3" width="7" height="7" />
                <rect x="14" y="14" width="7" height="7" />
                <rect x="3" y="14" width="7" height="7" />
              </svg>
              <span>{t("nav.dashboard")}</span>
            </button>
          </li>
          <li>
            <button
              type="button"
              className={`nav-sidebar-item ${currentPage === "analysis" ? "active" : ""}`}
              onClick={() => navigateTo("analysis")}
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
              </svg>
              <span>{t("nav.analysis")}</span>
            </button>
          </li>
          <li>
            <button
              type="button"
              className={`nav-sidebar-item ${currentPage === "areas" ? "active" : ""}`}
              onClick={() => navigateTo("areas")}
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6" />
                <line x1="8" y1="2" x2="8" y2="18" />
                <line x1="16" y1="6" x2="16" y2="22" />
              </svg>
              <span>{t("nav.areas")}</span>
            </button>
          </li>
          <li>
            <button
              type="button"
              className={`nav-sidebar-item ${currentPage === "profile" ? "active" : ""}`}
              onClick={() => navigateTo("profile")}
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                <circle cx="12" cy="7" r="4" />
              </svg>
              <span>{t("nav.profile")}</span>
            </button>
          </li>
        </ul>
        <div className="nav-sidebar-pin">
          <button
            type="button"
            className="nav-sidebar-item"
            onClick={onTogglePin}
            title={isPinned ? t("nav.collapse") : t("nav.keepOpen")}
          >
            {isPinned ? (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="11 17 6 12 11 7" />
                <polyline points="18 17 13 12 18 7" />
              </svg>
            ) : (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="6 17 11 12 6 7" />
                <polyline points="13 17 18 12 13 7" />
              </svg>
            )}
            <span>{isPinned ? t("nav.collapse") : t("nav.keepOpen")}</span>
          </button>
        </div>
        <div className="nav-sidebar-footer">
          <div className="d-flex align-items-center gap-3 w-100">
            {user?.picture ? (
              <img
                src={user.picture}
                alt={displayName}
                className="rounded-circle flex-shrink-0"
                width="36"
                height="36"
                referrerPolicy="no-referrer"
              />
            ) : (
              <span className="avatar-fallback rounded-circle flex-shrink-0">
                {displayName.charAt(0).toUpperCase()}
              </span>
            )}
            <div className="min-width-0">
              <div className="fw-medium small text-truncate">{displayName}</div>
              <button
                type="button"
                className="btn btn-link btn-sm p-0 text-muted"
                onClick={() =>
                  logout({ logoutParams: { returnTo: window.location.origin } })
                }
              >
                {t("common.logout")}
              </button>
            </div>
          </div>
        </div>
      </nav>
    </>
  );
}

export default Sidebar;
