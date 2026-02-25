import { useCallback, useState } from "react";
import { posthog } from "../config/posthogConfig";
import { faro } from "../config/faroConfig";

const CONSENT_KEY = "cookie_consent";

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

export default function useCookieConsent() {
  const [consent, setConsent] = useState(() => {
    const stored = localStorage.getItem(CONSENT_KEY);
    if (stored) applyConsent(stored);
    return stored;
  });

  const acceptCookies = useCallback(() => {
    localStorage.setItem(CONSENT_KEY, "accepted");
    setConsent("accepted");
    applyConsent("accepted");
  }, []);

  const rejectCookies = useCallback(() => {
    localStorage.setItem(CONSENT_KEY, "rejected");
    setConsent("rejected");
    applyConsent("rejected");
  }, []);

  return { consent, acceptCookies, rejectCookies };
}
