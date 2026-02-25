import posthogJs from "posthog-js";

const apiKey = process.env.REACT_APP_POSTHOG_KEY || "";
const apiHost = process.env.REACT_APP_POSTHOG_HOST || "https://us.i.posthog.com";

export const hasValidPosthogConfig = Boolean(apiKey);

let posthog = null;

if (hasValidPosthogConfig) {
  try {
    posthogJs.init(apiKey, {
      api_host: apiHost,
      capture_pageview: false, // We handle pageviews manually in useNavigation
      capture_pageleave: true,
      autocapture: true,
      disable_session_recording: true,
      opt_out_capturing_by_default: true,
    });
    posthog = posthogJs;
  } catch (error) {
    // eslint-disable-next-line no-console
    console.warn("Failed to initialize PostHog:", error);
  }
}

export { posthog };
