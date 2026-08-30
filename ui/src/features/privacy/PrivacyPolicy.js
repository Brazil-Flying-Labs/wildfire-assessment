import { useMemo } from "react";
import "./PrivacyPolicy.css";
import { useLanguage } from "../../context/LanguageContext";
import LanguageSelector from "../../LanguageSelector";

const CONTACT_EMAIL = "humanos@brazilflyinglabs.org.br";

function Section({ title, children }) {
  return (
    <div className="privacy-section">
      <h2 className="privacy-section-title">{title}</h2>
      {children}
    </div>
  );
}

function PrivacyPolicy({ onBack }) {
  const { t } = useLanguage();
  const logoSrc = useMemo(() => `${process.env.PUBLIC_URL}/logo.png`, []);

  return (
    <div className="landing-root d-flex flex-column min-vh-100">
      {/* Header */}
      <header className="landing-header">
        <div className="container d-flex align-items-center justify-content-between py-3">
          <div className="d-flex align-items-center gap-3">
            <img src={logoSrc} alt={t("landing.title")} className="landing-logo" />
            <span className="d-none d-md-inline landing-header-title">
              {t("landing.title")}
            </span>
          </div>
          <div className="d-flex align-items-center gap-2">
            <LanguageSelector className="form-select form-select-sm bg-transparent text-white border-secondary" />
            <button type="button" className="landing-btn-outline" onClick={onBack} style={{ padding: "6px 16px", fontSize: "14px" }}>
              {t("common.back")}
            </button>
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="privacy-content">
        <div className="container" style={{ maxWidth: "800px" }}>
          <h1 className="privacy-title">{t("privacy.title")}</h1>
          <p className="privacy-effective-date">{t("privacy.effectiveDate")}</p>
          <p className="privacy-text">{t("privacy.intro")}</p>

          {/* 1. Information We Collect */}
          <Section title={t("privacy.section1Title")}>
            <h3 className="privacy-subtitle">{t("privacy.section1Subtitle1")}</h3>
            <p className="privacy-text">{t("privacy.section1Text1")}</p>
            <h3 className="privacy-subtitle">{t("privacy.section1Subtitle2")}</h3>
            <p className="privacy-text">{t("privacy.section1Text2")}</p>
            <h3 className="privacy-subtitle">{t("privacy.section1Subtitle3")}</h3>
            <p className="privacy-text">{t("privacy.section1Text3")}</p>
            <h3 className="privacy-subtitle">{t("privacy.section1Subtitle5")}</h3>
            <p className="privacy-text">{t("privacy.section1Text5")}</p>
            <h3 className="privacy-subtitle">{t("privacy.section1Subtitle6")}</h3>
            <p className="privacy-text">{t("privacy.section1Text6")}</p>
          </Section>

          {/* 2. Information We Do Not Collect */}
          <Section title={t("privacy.section2Title")}>
            <p className="privacy-text">{t("privacy.section2Text")}</p>
          </Section>

          {/* 3. How We Use Your Information */}
          <Section title={t("privacy.section3Title")}>
            <p className="privacy-text">{t("privacy.section3Text")}</p>
          </Section>

          {/* 4. Third-Party Services */}
          <Section title={t("privacy.section4Title")}>
            <p className="privacy-text">{t("privacy.section4Text")}</p>
            <ul className="privacy-list">
              <li>{t("privacy.section4Item1")}</li>
              <li>{t("privacy.section4Item2")}</li>
              <li>{t("privacy.section4Item3")}</li>
              <li>{t("privacy.section4Item4")}</li>
            </ul>
          </Section>

          {/* 5. Cookies */}
          <Section title={t("privacy.section5Title")}>
            <p className="privacy-text">{t("privacy.section5Text")}</p>
          </Section>

          {/* 6. Data Storage and Security */}
          <Section title={t("privacy.section6Title")}>
            <p className="privacy-text">{t("privacy.section6Text")}</p>
          </Section>

          {/* 7. Your Rights */}
          <Section title={t("privacy.section7Title")}>
            <p className="privacy-text">{t("privacy.section7Text")}</p>
            <a href={`mailto:${CONTACT_EMAIL}`} className="privacy-link">{CONTACT_EMAIL}</a>
          </Section>

          {/* 8. Children's Privacy */}
          <Section title={t("privacy.section8Title")}>
            <p className="privacy-text">{t("privacy.section8Text")}</p>
          </Section>

          {/* 9. Changes to This Policy */}
          <Section title={t("privacy.section9Title")}>
            <p className="privacy-text">{t("privacy.section9Text")}</p>
          </Section>

          {/* 10. Contact Us */}
          <Section title={t("privacy.section10Title")}>
            <p className="privacy-text">{t("privacy.section10Text")}</p>
            <a href={`mailto:${CONTACT_EMAIL}`} className="privacy-link">{CONTACT_EMAIL}</a>
          </Section>
        </div>
      </main>

      {/* Footer */}
      <footer className="landing-footer py-4 text-center">
        <div className="container">{CONTACT_EMAIL}</div>
      </footer>
    </div>
  );
}

export default PrivacyPolicy;
