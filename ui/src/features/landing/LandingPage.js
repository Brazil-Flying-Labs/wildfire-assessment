import { useMemo } from "react";
import "./LandingPage.css";
import { useLanguage } from "../../context/LanguageContext";
import LanguageSelector from "../../LanguageSelector";

function LandingPage({ onLogin, isAuthenticated }) {
  const { t } = useLanguage();
  const logoSrc = useMemo(() => `${process.env.PUBLIC_URL}/logo.png`, []);
  const glowHero = useMemo(() => `${process.env.PUBLIC_URL}/glow-hero.svg`, []);
  const glowSection = useMemo(() => `${process.env.PUBLIC_URL}/glow-section.svg`, []);
  const screenshotSrc = useMemo(() => `${process.env.PUBLIC_URL}/front-end-screenshot.png`, []);
  const contactEmail = "humanos@brazilflyinglabs.org.br";

  return (
    <div className="landing-root d-flex flex-column min-vh-100">
      {/* ── Header ── */}
      <header className="landing-header">
        <div className="container d-flex align-items-center justify-content-between py-3">
          <div className="d-flex align-items-center gap-3">
            <img
              src={logoSrc}
              alt={t("landing.title")}
              className="landing-logo"
            />
            <span className="d-none d-md-inline landing-header-title">
              {t("landing.title")}
            </span>
          </div>
          <div className="d-flex align-items-center gap-2">
            <LanguageSelector className="form-select form-select-sm bg-transparent text-white border-secondary" />
            <button type="button" className="landing-btn-outline" onClick={onLogin} style={{ padding: "6px 16px", fontSize: "14px" }}>
              {isAuthenticated ? t("common.goToDashboard") : t("common.login")}
            </button>
          </div>
        </div>
      </header>

      {/* ── Hero ── */}
      <section className="landing-hero text-center">
        <img src={glowHero} alt="" aria-hidden="true" className="landing-glow" />
        <div className="container" style={{ position: "relative", zIndex: 1 }}>
          <h1 className="mb-4">
            {t("landing.title")}
          </h1>
          <p className="landing-subtitle mb-5">
            {t("landing.subtitle")}
          </p>
          <div className="d-flex flex-wrap justify-content-center gap-3">
            <button type="button" className="landing-btn-primary" onClick={onLogin}>
              {isAuthenticated ? t("common.goToDashboard") : t("common.accessPlatform")}
            </button>
            <a
              href={`mailto:${contactEmail}?subject=Demo%20Request%20-%20Wildfire%20Damage%20Assessment`}
              className="landing-btn-outline"
            >
              {t("common.requestDemo")}
            </a>
          </div>
        </div>
      </section>

      {/* ── Problem Statement ── */}
      <section className="landing-section">
        <div className="container" style={{ maxWidth: "800px" }}>
          <p className="landing-text mb-4">{t("landing.intro1")}</p>
          <p className="landing-text mb-4">{t("landing.intro2")}</p>
          <p className="landing-text landing-text-bright mb-4">{t("landing.intro3")}</p>
          <p className="landing-text-highlight" style={{ fontSize: "24px" }}>{t("landing.intro4")}</p>
        </div>
      </section>

      <hr className="landing-divider" />

      {/* ── Video ── */}
      <section className="landing-section" style={{ position: "relative", overflow: "hidden" }}>
        <img src={glowSection} alt="" aria-hidden="true" className="landing-glow" />
        <div className="container" style={{ maxWidth: "800px", position: "relative", zIndex: 1 }}>
          <div className="landing-video-wrapper">
            <iframe
              src="https://www.youtube.com/embed/9uFahhN7lGo"
              title={t("landing.videoTitle")}
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
              allowFullScreen
            ></iframe>
          </div>
        </div>
      </section>

      <hr className="landing-divider" />

      {/* ── Platform Features ── */}
      <section className="landing-section">
        <div className="container" style={{ maxWidth: "800px" }}>
          <h2 className="landing-section-heading text-center mb-4">
            {t("landing.platformTitle")}
          </h2>
          <p className="landing-text text-center mb-5">
            {t("landing.platformDesc")}
          </p>

          <div className="landing-card-lg">
            <p className="landing-text mb-4">{t("landing.platformAlgo")}</p>
            <ul className="landing-features mb-4">
              <li>{t("landing.feature1")}</li>
              <li>{t("landing.feature2")}</li>
              <li>{t("landing.feature3")}</li>
              <li>{t("landing.feature4")}</li>
              <li>{t("landing.feature5")}</li>
            </ul>
            <p className="landing-text-highlight mb-1">{t("landing.noExpertise")}</p>
            <p className="landing-text">{t("landing.fromRaw")}</p>
          </div>
        </div>
      </section>

      {/* ── Platform Screenshot ── */}
      <section className="landing-screenshot-section">
        <img src={glowSection} alt="" aria-hidden="true" className="landing-glow" />
        <div className="container" style={{ maxWidth: "800px", position: "relative", zIndex: 1 }}>
          <img
            src={screenshotSrc}
            alt={t("landing.platformTitle")}
            className="img-fluid landing-screenshot"
          />
        </div>
      </section>

      <hr className="landing-divider" />

      {/* ── Operations ── */}
      <section className="landing-section">
        <div className="container" style={{ maxWidth: "800px" }}>
          <h2 className="landing-section-heading text-center mb-4">
            {t("landing.operationsTitle")}
          </h2>
          <div className="landing-card">
            <p className="landing-text mb-4">{t("landing.operationsDesc")}</p>
            <p className="landing-text mb-0">{t("landing.operationsReadiness")}</p>
          </div>
        </div>
      </section>

      <hr className="landing-divider" />

      {/* ── Who It Serves ── */}
      <section className="landing-section">
        <div className="container" style={{ maxWidth: "800px" }}>
          <h2 className="landing-section-heading text-center mb-4">
            {t("landing.servesTitle")}
          </h2>
          <p className="landing-text text-center">{t("landing.servesDesc")}</p>
        </div>
      </section>

      <hr className="landing-divider" />

      {/* ── Beyond Assessment ── */}
      <section className="landing-section">
        <div className="container" style={{ maxWidth: "800px" }}>
          <h2 className="landing-section-heading text-center mb-4">
            {t("landing.beyondTitle")}
          </h2>
          <div className="landing-card">
            <p className="landing-text mb-4">{t("landing.beyondDesc1")}</p>
            <p className="landing-text mb-0">{t("landing.beyondDesc2")}</p>
          </div>
        </div>
      </section>

      <hr className="landing-divider" />

      {/* ── Why Now ── */}
      <section className="landing-section">
        <div className="container" style={{ maxWidth: "800px" }}>
          <h2 className="landing-section-heading text-center mb-4">
            {t("landing.whyNowTitle")}
          </h2>
          <p className="landing-text text-center mb-4">{t("landing.whyNowDesc")}</p>
          <p className="landing-text-highlight text-center" style={{ fontSize: "20px" }}>
            {t("landing.whyNowConclusion")}
          </p>
        </div>
      </section>

      <hr className="landing-divider" />

      {/* ── CTA ── */}
      <section className="landing-cta text-center">
        <img src={glowSection} alt="" aria-hidden="true" className="landing-glow" />
        <div className="container" style={{ maxWidth: "800px", position: "relative", zIndex: 1 }}>
          <h2 className="mb-4">{t("landing.ctaTitle")}</h2>
          <p className="landing-text text-center mb-3">{t("landing.ctaDesc")}</p>
          <p className="landing-text-highlight text-center mb-5">{t("landing.ctaAction")}</p>
          <div className="d-flex flex-wrap justify-content-center gap-3">
            <a
              href={`mailto:${contactEmail}?subject=Demo%20Request%20-%20Wildfire%20Damage%20Assessment`}
              className="landing-btn-primary"
            >
              {t("common.requestDemo")}
            </a>
            <a
              href={`mailto:${contactEmail}?subject=Partnership%20-%20Wildfire%20Damage%20Assessment`}
              className="landing-btn-outline"
            >
              {t("landing.partnerWithUs")}
            </a>
            <a
              href={`mailto:${contactEmail}?subject=Pilot%20Deployment%20-%20Wildfire%20Damage%20Assessment`}
              className="landing-btn-outline"
            >
              {t("landing.pilotPlatform")}
            </a>
          </div>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="landing-footer py-4 text-center">
        <div className="container">
          {contactEmail}
        </div>
      </footer>
    </div>
  );
}

export default LandingPage;
