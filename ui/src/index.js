import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';
import PrivacyPolicy from './features/privacy/PrivacyPolicy';
import reportWebVitals from './reportWebVitals';
import { LanguageProvider } from './context/LanguageContext';
import CookieConsentBanner from './components/CookieConsentBanner';

const root = ReactDOM.createRoot(document.getElementById('root'));

function AppWithProviders() {
  // Public privacy page — no authentication required
  if (window.location.pathname === "/privacy") {
    return <PrivacyPolicy onBack={() => window.history.back()} />;
  }

  return <App />;
}

root.render(
  <React.StrictMode>
    <LanguageProvider>
      <AppWithProviders />
      <CookieConsentBanner />
    </LanguageProvider>
  </React.StrictMode>
);

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
reportWebVitals();
