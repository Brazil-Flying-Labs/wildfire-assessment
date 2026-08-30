import { useCallback, useMemo, useState } from "react";
import { useLanguage } from "../../context/LanguageContext";

const inputClass = "form-control form-control-lg text-center";

export function AuthPageShell({ children, logoSrc }) {
  return (
    <div className="app-root d-flex align-items-center justify-content-center min-vh-100">
      <div className="text-center p-4" style={{ maxWidth: 420, width: "100%" }}>
        <img src={logoSrc} alt="" className="brand-logo mb-4" />
        {children}
      </div>
    </div>
  );
}

export function LoginPage({ baseUrl, onLoginSuccess, onBackToLanding, fetchJson }) {
  const { t } = useLanguage();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errorKey, setErrorKey] = useState(null);
  const [busy, setBusy] = useState(false);

  const submit = useCallback(
    async (event) => {
      event.preventDefault();
      setBusy(true);
      setErrorKey(null);
      try {
        const response = await fetchJson(`${baseUrl}/auth/login/`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, password }),
        });
        if (response.ok) {
          onLoginSuccess();
        } else if (response.status === 403) {
          setErrorKey("auth.accountPending");
        } else {
          setErrorKey("auth.loginFailed");
        }
      } catch {
        setErrorKey("auth.loginFailed");
      } finally {
        setBusy(false);
      }
    },
    [baseUrl, email, password, fetchJson, onLoginSuccess]
  );

  return (
    <AuthPageShell>
      <h2>{t("auth.loginTitle")}</h2>
      <form onSubmit={submit} className="mt-4 text-start">
        <div className="mb-3">
          <label className="form-label">{t("auth.email")}</label>
          <input
            type="email"
            className={inputClass}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="email"
          />
        </div>
        <div className="mb-3">
          <label className="form-label">{t("auth.password")}</label>
          <input
            type="password"
            className={inputClass}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoComplete="current-password"
          />
        </div>
        {errorKey && (
          <div className="alert alert-danger py-2" role="alert">
            {t(errorKey)}
          </div>
        )}
        <button type="submit" className="btn btn-primary w-100" disabled={busy}>
          {t("auth.loginButton")}
        </button>
      </form>
      <div className="mt-3">
        <a href="/reset-password" className="small">
          {t("auth.forgotPassword")}
        </a>
      </div>
      <button
        type="button"
        className="btn btn-link mt-2"
        onClick={onBackToLanding}
      >
        {t("auth.backToLanding")}
      </button>
    </AuthPageShell>
  );
}

export function SetPasswordPage({ baseUrl, fetchJson }) {
  const { t } = useLanguage();
  const [password, setPassword] = useState("");
  const [done, setDone] = useState(false);
  const [errorKey, setErrorKey] = useState(null);
  const [busy, setBusy] = useState(false);

  const { uidb64, token } = useMemo(() => {
    const parts = window.location.pathname.split("/");
    // /set-password/<uidb64>/<token>/
    return { uidb64: parts[2] || "", token: parts[3] || "" };
  }, []);

  const submit = useCallback(
    async (event) => {
      event.preventDefault();
      setBusy(true);
      setErrorKey(null);
      try {
        const response = await fetchJson(`${baseUrl}/auth/set-password/`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ uidb64, token, password }),
        });
        if (response.ok) {
          setDone(true);
        } else {
          setErrorKey("auth.setPasswordInvalid");
        }
      } catch {
        setErrorKey("auth.setPasswordInvalid");
      } finally {
        setBusy(false);
      }
    },
    [baseUrl, fetchJson, password, token, uidb64]
  );

  return (
    <AuthPageShell>
      {done ? (
        <>
          <h2>{t("auth.setPasswordSuccess")}</h2>
          <a href="/login" className="btn btn-primary mt-4">
            {t("auth.goToLogin")}
          </a>
        </>
      ) : (
        <>
          <h2>{t("auth.setPasswordTitle")}</h2>
          <p className="text-muted">{t("auth.setPasswordSubtitle")}</p>
          <form onSubmit={submit} className="mt-4 text-start">
            <div className="mb-3">
              <label className="form-label">{t("auth.newPassword")}</label>
              <input
                type="password"
                className={inputClass}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="new-password"
                minLength={8}
              />
            </div>
            {errorKey && (
              <div className="alert alert-danger py-2" role="alert">
                {t(errorKey)}
              </div>
            )}
            <button type="submit" className="btn btn-primary w-100" disabled={busy}>
              {t("auth.setPasswordButton")}
            </button>
          </form>
        </>
      )}
    </AuthPageShell>
  );
}

export function ResetPasswordPage({ baseUrl, fetchJson, onBackToLanding }) {
  const { t } = useLanguage();
  const [email, setEmail] = useState("");
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);

  const submit = useCallback(
    async (event) => {
      event.preventDefault();
      setBusy(true);
      try {
        await fetchJson(`${baseUrl}/auth/reset-password/`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email }),
        });
        setDone(true);
      } catch {
        setDone(true); // generic response — never reveal e-mail state
      } finally {
        setBusy(false);
      }
    },
    [baseUrl, email, fetchJson]
  );

  return (
    <AuthPageShell>
      {done ? (
        <>
          <h2>{t("auth.resetSuccess")}</h2>
          <a href="/login" className="btn btn-primary mt-4">
            {t("auth.goToLogin")}
          </a>
        </>
      ) : (
        <>
          <h2>{t("auth.resetTitle")}</h2>
          <p className="text-muted">{t("auth.resetSubtitle")}</p>
          <form onSubmit={submit} className="mt-4 text-start">
            <div className="mb-3">
              <label className="form-label">{t("auth.email")}</label>
              <input
                type="email"
                className={inputClass}
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
              />
            </div>
            <button type="submit" className="btn btn-primary w-100" disabled={busy}>
              {t("auth.resetButton")}
            </button>
          </form>
          <button
            type="button"
            className="btn btn-link mt-2"
            onClick={onBackToLanding}
          >
            {t("auth.backToLanding")}
          </button>
        </>
      )}
    </AuthPageShell>
  );
}
