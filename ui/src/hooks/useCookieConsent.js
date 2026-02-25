import { useCallback, useEffect, useState } from "react";
import { posthog } from "../config/posthogConfig";
import { faro } from "../config/faroConfig";

const CONSENT_KEY = "cookie_consent";
const CONSENT_EVENT = "cookie_consent_changed";

function applyConsent(value) {
  if (posthog) {
    if (value === "accepted") {
      posthog.opt_in_capturing();
    } else {
      posthog.opt_out_capturing();
    }
  }
  if (faro) {
    if (value === "accepted") {
      faro.unpause();
    } else {
      faro.pause();
    }
  }
}

function broadcast(value) {
  window.dispatchEvent(new CustomEvent(CONSENT_EVENT, { detail: value }));
}

export default function useCookieConsent() {
  const [consent, setConsent] = useState(() => {
    const stored = localStorage.getItem(CONSENT_KEY);
    if (stored) applyConsent(stored);
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
    applyConsent("accepted");
    broadcast("accepted");
  }, []);

  const rejectCookies = useCallback(() => {
    localStorage.setItem(CONSENT_KEY, "rejected");
    setConsent("rejected");
    applyConsent("rejected");
    broadcast("rejected");
  }, []);

  const resetConsent = useCallback(() => {
    localStorage.removeItem(CONSENT_KEY);
    setConsent(null);
    applyConsent("rejected");
    broadcast(null);
  }, []);

  return { consent, acceptCookies, rejectCookies, resetConsent };
}
