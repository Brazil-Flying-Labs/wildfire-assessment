import LanguageSelector from "../../LanguageSelector";
import NotificationBell from "../notifications/NotificationBell";

function AppHeader({
  toggleNav,
  navigateTo,
  logoSrc,
  user,
  displayName,
  logout,
  notificationBellProps,
  t,
}) {
  return (
    <header className="app-header text-white">
      <div className="container-fluid d-flex align-items-center justify-content-between py-3 gap-3">
        <div className="d-flex align-items-center gap-2 gap-md-3 header-brand">
          <button
            type="button"
            className="btn btn-link text-white p-0 nav-toggle-btn"
            onClick={toggleNav}
            aria-label="Toggle navigation"
          >
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="3" y1="6" x2="21" y2="6" />
              <line x1="3" y1="12" x2="21" y2="12" />
              <line x1="3" y1="18" x2="21" y2="18" />
            </svg>
          </button>
          <button
            type="button"
            className="btn p-0 border-0 bg-transparent header-logo-btn"
            onClick={() => navigateTo("dashboard")}
            aria-label={t("landing.title")}
          >
            <img
              src={logoSrc}
              alt={t("landing.title")}
              className="brand-logo"
            />
          </button>
          <div className="d-none d-md-block">
            <h1 className="h4 mb-0">{t("app.title")}</h1>
          </div>
        </div>

        <div className="d-flex align-items-center gap-2 header-actions">
          <LanguageSelector />
          <NotificationBell {...notificationBellProps} />
          <div className="avatar-menu">
            {user?.picture ? (
              <img
                src={user.picture}
                alt={displayName}
                title={displayName}
                className="rounded-circle avatar-trigger"
                width="32"
                height="32"
                referrerPolicy="no-referrer"
              />
            ) : (
              <span className="avatar-fallback rounded-circle avatar-trigger">
                {displayName.charAt(0).toUpperCase()}
              </span>
            )}
            <div className="avatar-dropdown">
              <div className="avatar-dropdown-inner">
                <p className="avatar-dropdown-name">{displayName}</p>
                <button
                  type="button"
                  className="btn btn-outline-light btn-sm w-100"
                  onClick={() =>
                    logout({ logoutParams: { returnTo: window.location.origin } })
                  }
                >
                  {t("common.logout")}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}

export default AppHeader;
