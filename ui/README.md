# Wildfire Assessment UI

React interface responsible for interacting with the wildfire assessment API. The application now enforces Auth0 authentication before granting access to protected resources.

## Prerequisites

- Node.js 16+ (use the version supported by the project)
- Auth0 account and application with Refresh Token Rotation enabled

## Environment variables

Create a `.env.local` file inside the `ui` folder with the values below:

```
REACT_APP_WILDLIFE_API_URL=https://your-api.example.com
REACT_APP_AUTH0_DOMAIN=example-region.auth0.com
REACT_APP_AUTH0_CLIENT_ID=xxxxxxxxxxxxxxxxxxxxxxx
REACT_APP_AUTH0_AUDIENCE=https://your-api.example.com
```

> Notes
>
> - `REACT_APP_WILDLIFE_API_URL` remains mandatory just like in the previous versions.
> - The domain, client ID, and audience must match the API configured in Auth0.
> - The Auth0Provider uses `useRefreshTokens` and `cacheLocation="localstorage"`, so enable Refresh Token Rotation for this application in the Auth0 dashboard.

## Scripts

Inside the `ui` directory run:

- `npm start` — starts the development server at `http://localhost:3000`.
- `npm run build` — generates the production bundle inside `ui/build`.
- `npm test` — runs the default Create React App test suite.

## Authentication flow

- Unauthenticated users are redirected to Auth0 immediately.
- After login, each API call (`/ecological_reserve/` and `/analyze/`) sends the `Authorization: Bearer <token>` header obtained via `getAccessTokenSilently`.
- Refresh tokens help keep the session valid without prompting the user again until Auth0 requires it.

If any Auth0 parameter is missing, the interface shows an explanatory message instead of starting normally.
