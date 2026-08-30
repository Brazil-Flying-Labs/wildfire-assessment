// jest-dom adds custom jest matchers for asserting on DOM nodes.
// allows you to do things like:
// expect(element).toHaveTextContent(/react/i)
// learn more: https://github.com/testing-library/jest-dom
import '@testing-library/jest-dom';

// react-markdown@10 is ESM-only and its dependency tree relies on package
// "exports" maps that jest 27 (react-scripts 5) cannot resolve. Rendering
// markdown is not what these tests verify, so stub it at the module
// boundary: components keep importing it, tests keep working.
jest.mock('react-markdown', () => ({
  __esModule: true,
  default: ({ children }) => children,
}));

// react-leaflet@5 is ESM-only with the same jest 27 limitation. Maps are
// not exercised by these tests, so render children and drop map internals.
jest.mock('react-leaflet', () => ({
  __esModule: true,
  MapContainer: ({ children }) => children,
  TileLayer: () => null,
  GeoJSON: () => null,
  CircleMarker: () => null,
  Popup: ({ children }) => children,
  useMap: () => ({}),
}));

// react-day-picker@9 ships dual builds whose subpath resolution requires
// package "exports" support, which jest 27 does not have.
jest.mock('react-day-picker', () => ({
  __esModule: true,
  DayPicker: () => null,
}));
