import { useLanguage, SUPPORTED_LANGUAGES } from "./LanguageContext";

const LABELS = {
  en: "\ud83c\uddfa\ud83c\uddf8 EN",
  "pt-BR": "\ud83c\udde7\ud83c\uddf7 PT",
  fr: "\ud83c\uddeb\ud83c\uddf7 FR",
};

function LanguageSelector({ className }) {
  const { language, setLanguage } = useLanguage();

  return (
    <select
      className={className || "form-select form-select-sm"}
      style={{ width: "auto", minWidth: "60px" }}
      value={language}
      onChange={(e) => setLanguage(e.target.value)}
      aria-label="Select language"
    >
      {SUPPORTED_LANGUAGES.map((lang) => (
        <option key={lang} value={lang}>
          {LABELS[lang] || lang}
        </option>
      ))}
    </select>
  );
}

export default LanguageSelector;
