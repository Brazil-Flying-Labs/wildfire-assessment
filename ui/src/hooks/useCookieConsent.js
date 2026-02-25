import { useCallback, useEffect, useState } from "react";
import { posthog } from "../config/posthogConfig";
import { faro } from "../config/faroConfig";

const CONSENT_KEY = "cookie_consent";

function applyConsent(value) {
  const isAccepted = value === "accepted" || value === true;
  if (posthog) {
    if (isAccepted) {
      posthog.opt_in_capturing();
    } else {
      posthog.opt_out_capturing();
    }
  }
  if (faro) {
    if (isAccepted) {
      faro.unpause();
    } else {
      faro.pause();
    }
  }
}

// Convert backend boolean to frontend string format
function boolToConsent(value) {
  if (value === true) return "accepted";
  if (value === false) return "rejected";
  return null;
}

// Convert frontend string to backend boolean format
function consentToBool(value) {
  if (value === "accepted") return true;
  if (value === "rejected") return false;
  return null;
}

export default function useCookieConsent(authorizedFetch, baseUrl, backendProfile) {
  const [consent, setConsent] = useState(() => {
    // First check localStorage for immediate value
    const stored = localStorage.getItem(CONSENT_KEY);
    if (stored) applyConsent(stored);
    return stored;
  });

  // Sync from backend profile when it loads
  useEffect(() => {
    if (backendProfile?.cookie_consent !== undefined && backendProfile?.cookie_consent !== null) {
      const backendConsent = boolToConsent(backendProfile.cookie_consent);
      if (backendConsent && backendConsent !== consent) {
        localStorage.setItem(CONSENT_KEY, backendConsent);
        setConsent(backendConsent);
        applyConsent(backendConsent);
      }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [backendProfile?.cookie_consent]);

  const updateConsent = useCallback(async (newConsent) => {
    localStorage.setItem(CONSENT_KEY, newConsent);
    setConsent(newConsent);
    applyConsent(newConsent);

    // Sync to backend if available
    if (authorizedFetch && baseUrl) {
      try {
        await authorizedFetch(`${baseUrl}/me/`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ cookie_consent: consentToBool(newConsent) }),
        });
      } catch (error) {
        console.error("Failed to sync cookie consent to backend:", error);
      }
    }
  }, [authorizedFetch, baseUrl]);

  const acceptCookies = useCallback(() => {
    updateConsent("accepted");
  }, [updateConsent]);

  const rejectCookies = useCallback(() => {
    updateConsent("rejected");
  }, [updateConsent]);

  return { consent, acceptCookies, rejectCookies };
}
