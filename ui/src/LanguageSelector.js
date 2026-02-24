import { useState, useRef, useCallback } from "react";
import { useLanguage, SUPPORTED_LANGUAGES } from "./context/LanguageContext";
import useClickOutside from "./hooks/useClickOutside";

const FLAGS = {
  en: "\ud83c\uddfa\ud83c\uddf8",
  "pt-BR": "\ud83c\udde7\ud83c\uddf7",
  fr: "\ud83c\uddeb\ud83c\uddf7",
};

const LABELS = {
  en: "English",
  "pt-BR": "Portugu\u00eas",
  fr: "Fran\u00e7ais",
};

function LanguageSelector() {
  const { language, setLanguage } = useLanguage();
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef(null);

  const close = useCallback(() => setIsOpen(false), []);
  const toggle = useCallback(() => setIsOpen((prev) => !prev), []);

  const select = useCallback(
    (lang) => {
      setLanguage(lang);
      setIsOpen(false);
    },
    [setLanguage]
  );

  useClickOutside(menuRef, close, isOpen);

  return (
    <div className="lang-selector" ref={menuRef}>
      <button
        type="button"
        className="lang-selector-trigger"
        onClick={toggle}
        aria-label="Select language"
        title={LABELS[language]}
      >
        <span className="lang-flag">{FLAGS[language]}</span>
      </button>
      {isOpen && (
        <div className="lang-selector-dropdown">
          {SUPPORTED_LANGUAGES.map((lang) => (
            <button
              key={lang}
              type="button"
              className={`lang-selector-option ${lang === language ? "active" : ""}`}
              onClick={() => select(lang)}
            >
              <span className="lang-flag">{FLAGS[lang]}</span>
              <span>{LABELS[lang]}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export default LanguageSelector;
