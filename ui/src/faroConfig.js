import {
  getWebInstrumentations,
  initializeFaro,
} from "@grafana/faro-web-sdk";
import { TracingInstrumentation } from "@grafana/faro-web-tracing";

const collectorUrl = process.env.REACT_APP_FARO_COLLECTOR_URL || "";
const appName = process.env.REACT_APP_FARO_APP_NAME || "wildfire-ui";

const UI_VERSION = "1.4.8";

export const hasValidFaroConfig = Boolean(collectorUrl);

let faro = null;

if (hasValidFaroConfig) {
  try {
    faro = initializeFaro({
      url: collectorUrl,
      app: {
        name: appName,
        version: UI_VERSION,
        environment: process.env.REACT_APP_FARO_ENVIRONMENT || "local",
      },
      instrumentations: [
        ...getWebInstrumentations({
          captureConsole: true,
        }),
        new TracingInstrumentation(),
      ],
      sessionTracking: {
        enabled: true,
      },
    });
  } catch (error) {
    // eslint-disable-next-line no-console
    console.warn("Failed to initialize Grafana Faro:", error);
  }
}

export { faro };
