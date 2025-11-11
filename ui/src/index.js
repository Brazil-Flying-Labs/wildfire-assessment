import React from 'react';
import ReactDOM from 'react-dom/client';
import { Auth0Provider } from '@auth0/auth0-react';
import './index.css';
import App from './App';
import reportWebVitals from './reportWebVitals';
import { authConfig, hasValidAuthConfig } from './authConfig';

const root = ReactDOM.createRoot(document.getElementById('root'));

function MissingAuthConfiguration() {
  return (
    <div className="app-root d-flex align-items-center justify-content-center min-vh-100">
      <div className="alert alert-danger m-4" role="alert">
        Variáveis de ambiente do Auth0 não configuradas. Configure{' '}
        <code className="mx-1">REACT_APP_AUTH0_DOMAIN</code>,{' '}
        <code className="mx-1">REACT_APP_AUTH0_CLIENT_ID</code> e{' '}
        <code className="mx-1">REACT_APP_AUTH0_AUDIENCE</code> antes de
        iniciar o aplicativo.
      </div>
    </div>
  );
}

function AppWithProviders() {
  if (!hasValidAuthConfig) {
    return <MissingAuthConfiguration />;
  }

  return (
    <Auth0Provider
      domain={authConfig.domain}
      clientId={authConfig.clientId}
      authorizationParams={{
        redirect_uri: authConfig.redirectUri,
        audience: authConfig.audience,
      }}
      cacheLocation="localstorage"
      useRefreshTokens
    >
      <App />
    </Auth0Provider>
  );
}

root.render(
  <React.StrictMode>
    <AppWithProviders />
  </React.StrictMode>
);

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
reportWebVitals();
