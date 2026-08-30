import { render, screen } from '@testing-library/react';
import App from './App';
import { LanguageProvider } from './context/LanguageContext';

test('renders the landing page when there is no active session', async () => {
  // The app checks the session on boot: CSRF cookie, then /me/ (401 here).
  global.fetch = jest.fn((url) => {
    if (String(url).endsWith('/auth/csrf/')) {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => ({ csrfToken: 'test-token' }),
      });
    }
    if (String(url).endsWith('/me/')) {
      return Promise.resolve({ ok: false, status: 401, json: async () => ({}) });
    }
    return Promise.resolve({ ok: true, status: 200, json: async () => ({}) });
  });

  render(
    <LanguageProvider>
      <App />
    </LanguageProvider>
  );

  expect(
    await screen.findByRole('heading', {
      name: /wildfire insight intelligence/i,
    })
  ).toBeInTheDocument();
});
