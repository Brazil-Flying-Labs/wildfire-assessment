import {
  getWebInstrumentations,
  initializeFaro,
} from "@grafana/faro-web-sdk";
import { TracingInstrumentation } from "@grafana/faro-web-tracing";
import { UI_VERSION, APP_ENVIRONMENT } from "../constants/config";

const collectorUrl = process.env.REACT_APP_FARO_COLLECTOR_URL || "";
const appName = process.env.REACT_APP_FARO_APP_NAME || "wildfire-ui";

export const hasValidFaroConfig = Boolean(collectorUrl);

let faro = null;

if (hasValidFaroConfig) {
  try {
    faro = initializeFaro({
      url: collectorUrl,
      app: {
        name: appName,
        version: UI_VERSION,
        environment: APP_ENVIRONMENT,
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
      paused: true,
    });
  } catch (error) {
    // eslint-disable-next-line no-console
    console.warn("Failed to initialize Grafana Faro:", error);
  }
}

export { faro };
