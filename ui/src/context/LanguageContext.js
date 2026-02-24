import { createContext, useCallback, useContext, useMemo, useState } from "react";
import en from "../translations/en.json";
import ptBR from "../translations/pt-BR.json";
import fr from "../translations/fr.json";

const SUPPORTED_LANGUAGES = ["en", "pt-BR", "fr"];
const STORAGE_KEY = "preferred_language";

const translationMap = { en, "pt-BR": ptBR, fr };

function detectBrowserLanguage() {
  const nav = navigator.language || "";
  if (nav.startsWith("pt")) return "pt-BR";
  if (nav.startsWith("fr")) return "fr";
  return "en";
}

function getInitialLanguage() {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored && SUPPORTED_LANGUAGES.includes(stored)) {
    return stored;
  }
  return detectBrowserLanguage();
}

const LanguageContext = createContext(null);

export function LanguageProvider({ children }) {
  const [language, setLanguageState] = useState(getInitialLanguage);

  const setLanguage = useCallback((lang) => {
    if (SUPPORTED_LANGUAGES.includes(lang)) {
      setLanguageState(lang);
      localStorage.setItem(STORAGE_KEY, lang);
    }
  }, []);

  const t = useCallback(
    (key, params) => {
      const strings = translationMap[language] || translationMap.en;
      let value = strings[key] || translationMap.en[key] || key;
      if (params) {
        Object.entries(params).forEach(([k, v]) => {
          value = value.replace(new RegExp(`\\{${k}\\}`, "g"), v);
        });
      }
      return value;
    },
    [language]
  );

  const contextValue = useMemo(
    () => ({ language, setLanguage, t }),
    [language, setLanguage, t]
  );

  return (
    <LanguageContext.Provider value={contextValue}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const ctx = useContext(LanguageContext);
  if (!ctx) {
    throw new Error("useLanguage must be used within a LanguageProvider");
  }
  return ctx;
}

export { SUPPORTED_LANGUAGES };
