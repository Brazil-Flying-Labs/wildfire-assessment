const domain = process.env.REACT_APP_AUTH0_DOMAIN || "";
const clientId = process.env.REACT_APP_AUTH0_CLIENT_ID || "";
const audience = process.env.REACT_APP_AUTH0_AUDIENCE || "";
const redirectUri =
  typeof window !== "undefined" && window.location
    ? window.location.origin
    : "";

const missingKeys = [];

if (!domain) missingKeys.push("REACT_APP_AUTH0_DOMAIN");
if (!clientId) missingKeys.push("REACT_APP_AUTH0_CLIENT_ID");
if (!audience) missingKeys.push("REACT_APP_AUTH0_AUDIENCE");

if (missingKeys.length) {
  // eslint-disable-next-line no-console
  console.warn(
    `Auth0 configuration missing environment variables: ${missingKeys.join(", ")}`
  );
}

export const authConfig = {
  domain,
  clientId,
  audience,
  redirectUri,
};
export const hasValidAuthConfig = missingKeys.length === 0;
