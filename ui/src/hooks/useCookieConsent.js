import { useCallback, useEffect, useState } from "react";

const CONSENT_KEY = "cookie_consent";
const CONSENT_EVENT = "cookie_consent_changed";

function broadcast(value) {
  window.dispatchEvent(new CustomEvent(CONSENT_EVENT, { detail: value }));
}

export default function useCookieConsent() {
  const [consent, setConsent] = useState(() => {
    const stored = localStorage.getItem(CONSENT_KEY);
    return stored;
  });

  useEffect(() => {
    const handler = (e) => setConsent(e.detail);
    window.addEventListener(CONSENT_EVENT, handler);
    return () => window.removeEventListener(CONSENT_EVENT, handler);
  }, []);

  const acceptCookies = useCallback(() => {
    localStorage.setItem(CONSENT_KEY, "accepted");
    setConsent("accepted");
    broadcast("accepted");
  }, []);

  const rejectCookies = useCallback(() => {
    localStorage.setItem(CONSENT_KEY, "rejected");
    setConsent("rejected");
    broadcast("rejected");
  }, []);

  const resetConsent = useCallback(() => {
    localStorage.removeItem(CONSENT_KEY);
    setConsent(null);
    broadcast(null);
  }, []);

  return { consent, acceptCookies, rejectCookies, resetConsent };
}
