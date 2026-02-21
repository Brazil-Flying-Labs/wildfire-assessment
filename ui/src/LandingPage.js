import { useMemo } from "react";
import "./LandingPage.css";
import { useLanguage } from "./LanguageContext";
import LanguageSelector from "./LanguageSelector";

function LandingPage({ onLogin, isAuthenticated }) {
  const { t } = useLanguage();
  const logoSrc = useMemo(() => `${process.env.PUBLIC_URL}/logo.png`, []);
  const contactEmail = "humanos@brazilflyinglabs.org.br";

  return (
    <div className="landing-root d-flex flex-column min-vh-100">
      <header className="landing-header text-white">
        <div className="container d-flex align-items-center justify-content-between py-3">
          <div className="d-flex align-items-center gap-3">
            <img
              src={logoSrc}
              alt={t("landing.title")}
              className="landing-logo"
            />
            <span className="d-none d-md-inline fw-semibold">
              {t("landing.title")}
            </span>
          </div>
          <div className="d-flex align-items-center gap-2">
            <LanguageSelector className="form-select form-select-sm bg-transparent text-white border-light" />
            <button
              type="button"
              className="btn btn-outline-light btn-sm"
              onClick={onLogin}
            >
              {isAuthenticated ? t("common.goToDashboard") : t("common.login")}
            </button>
          </div>
        </div>
      </header>

      <section className="landing-hero text-white text-center">
        <div className="container py-5">
          <h1 className="display-5 fw-bold mb-3">
            {t("landing.title")}
          </h1>
          <p className="lead mb-4 mx-auto" style={{ maxWidth: "720px" }}>
            {t("landing.subtitle")}
          </p>
          <div className="d-flex flex-wrap justify-content-center gap-3">
            <button
              type="button"
              className="btn btn-light btn-lg"
              onClick={onLogin}
            >
              {isAuthenticated ? t("common.goToDashboard") : t("common.accessPlatform")}
            </button>
            <a
              href={`mailto:${contactEmail}?subject=Demo%20Request%20-%20Wildfire%20Damage%20Assessment`}
              className="btn btn-outline-light btn-lg"
            >
              {t("common.requestDemo")}
            </a>
          </div>
        </div>
      </section>

      <section className="py-5 bg-white">
        <div className="container" style={{ maxWidth: "800px" }}>
          <p className="text-muted mb-4">{t("landing.intro1")}</p>
          <p className="text-muted mb-4">{t("landing.intro2")}</p>
          <p className="fw-semibold text-body mb-4">{t("landing.intro3")}</p>
          <p className="fw-bold text-body fs-5">{t("landing.intro4")}</p>
        </div>
      </section>

      <section className="py-5 bg-light">
        <div className="container" style={{ maxWidth: "800px" }}>
          <div className="landing-video-wrapper mb-4">
            <iframe
              src="https://www.youtube.com/embed/9uFahhN7lGo"
              title={t("landing.videoTitle")}
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
              allowFullScreen
            ></iframe>
          </div>
        </div>
      </section>

      <section className="py-5 bg-white">
        <div className="container" style={{ maxWidth: "800px" }}>
          <h2 className="h3 fw-bold mb-3">{t("landing.platformTitle")}</h2>
          <p className="text-muted mb-4">{t("landing.platformDesc")}</p>
          <p className="text-muted mb-3">{t("landing.platformAlgo")}</p>
          <ul className="text-muted mb-4">
            <li>{t("landing.feature1")}</li>
            <li>{t("landing.feature2")}</li>
            <li>{t("landing.feature3")}</li>
            <li>{t("landing.feature4")}</li>
            <li>{t("landing.feature5")}</li>
          </ul>
          <p className="fw-semibold text-body mb-1">{t("landing.noExpertise")}</p>
          <p className="text-muted mb-4">{t("landing.fromRaw")}</p>
          <img
            src={`${process.env.PUBLIC_URL}/front-end-screenshot.png`}
            alt={t("landing.platformTitle")}
            className="img-fluid rounded shadow"
          />
        </div>
      </section>

      <section className="py-5 bg-light">
        <div className="container" style={{ maxWidth: "800px" }}>
          <h2 className="h3 fw-bold mb-3">{t("landing.operationsTitle")}</h2>
          <p className="text-muted mb-4">{t("landing.operationsDesc")}</p>
          <p className="text-muted">{t("landing.operationsReadiness")}</p>
        </div>
      </section>

      <section className="py-5 bg-white">
        <div className="container" style={{ maxWidth: "800px" }}>
          <h2 className="h3 fw-bold mb-3">{t("landing.servesTitle")}</h2>
          <p className="text-muted">{t("landing.servesDesc")}</p>
        </div>
      </section>

      <section className="py-5 bg-light">
        <div className="container" style={{ maxWidth: "800px" }}>
          <h2 className="h3 fw-bold mb-3">{t("landing.beyondTitle")}</h2>
          <p className="text-muted mb-4">{t("landing.beyondDesc1")}</p>
          <p className="text-muted">{t("landing.beyondDesc2")}</p>
        </div>
      </section>

      <section className="py-5 bg-white">
        <div className="container" style={{ maxWidth: "800px" }}>
          <h2 className="h3 fw-bold mb-3">{t("landing.whyNowTitle")}</h2>
          <p className="text-muted mb-4">{t("landing.whyNowDesc")}</p>
          <p className="fw-semibold text-body">{t("landing.whyNowConclusion")}</p>
        </div>
      </section>

      <section className="landing-cta text-white text-center py-5">
        <div className="container" style={{ maxWidth: "800px" }}>
          <h2 className="h3 fw-bold mb-3">{t("landing.ctaTitle")}</h2>
          <p className="mb-4">{t("landing.ctaDesc")}</p>
          <p className="fw-semibold mb-4">{t("landing.ctaAction")}</p>
          <div className="d-flex flex-wrap justify-content-center gap-3">
            <a
              href={`mailto:${contactEmail}?subject=Demo%20Request%20-%20Wildfire%20Damage%20Assessment`}
              className="btn btn-light"
            >
              {t("common.requestDemo")}
            </a>
            <a
              href={`mailto:${contactEmail}?subject=Partnership%20-%20Wildfire%20Damage%20Assessment`}
              className="btn btn-outline-light"
            >
              {t("landing.partnerWithUs")}
            </a>
            <a
              href={`mailto:${contactEmail}?subject=Pilot%20Deployment%20-%20Wildfire%20Damage%20Assessment`}
              className="btn btn-outline-light"
            >
              {t("landing.pilotPlatform")}
            </a>
          </div>
        </div>
      </section>

      <footer className="landing-footer py-3 text-center small text-white">
        <div className="container">
          {contactEmail}
        </div>
      </footer>
    </div>
  );
}

export default LandingPage;
