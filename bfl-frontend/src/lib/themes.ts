export type Theme = 'light' | 'dark' | 'forest';

export const themes: Theme[] = ['light', 'dark', 'forest'];

export function isValidTheme(theme: string): theme is Theme {
  return themes.includes(theme as Theme);
}
