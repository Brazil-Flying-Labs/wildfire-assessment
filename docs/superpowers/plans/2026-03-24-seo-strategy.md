# SEO Strategy — Wildfire Insight Intelligence

> **For agentic workers:** Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Maximize Google Search visibility for the landing page and privacy policy — the only public pages on a login-gated SPA.

**Architecture:** Pure client-side React 19 SPA on CloudFront + S3. No SSR. Google renders JS well, but meta tags in `index.html` are the primary SEO signal for all crawlers. The site supports 4 languages (en, pt-BR, es-ES, fr) but uses a single URL with client-side language switching — no separate language URLs exist today.

**Production URL:** `https://wildfire.droneai.com.br`
**Dev URL:** `https://wildfire-dev.droneai.com.br`

---

## Current State

| Area | Status | Impact |
|------|--------|--------|
| Meta description | Generic ("Monitoring areas affected...") | HIGH — poor click-through rate |
| Open Graph | Only `og:description` | HIGH — poor social sharing |
| Twitter Cards | Missing | MEDIUM — no Twitter previews |
| Structured data | None | HIGH — no rich results |
| Canonical URL | Missing | HIGH — potential duplicate content |
| Hreflang | Missing | MEDIUM — 4 languages not declared |
| Sitemap | Missing | MEDIUM — crawlers can't discover pages |
| robots.txt | No sitemap ref, no path restrictions | LOW — permissive but incomplete |
| Page title | "Wildfire assessment" (generic) | HIGH — poor search appearance |
| Web manifest | Empty name/short_name | LOW — PWA signal |
| Favicons | Present but inconsistent references | LOW |

## Strategy Overview

Since this is a login-gated SPA with only 2 public pages (`/` and `/privacy`), the strategy focuses on maximizing the quality of those pages rather than content volume. The landing page is content-rich and well-structured — it just needs proper technical SEO signals.

**Priority order:**
1. Meta tags & Open Graph (biggest impact, simplest change)
2. Structured data (rich results in SERP)
3. Sitemap + robots.txt (crawler guidance)
4. Hreflang (multilingual signals)
5. Performance & Core Web Vitals
6. AI search readiness

---

## Task 1: Optimize `index.html` Meta Tags

**Files:**
- Modify: `ui/public/index.html`

This is the single highest-impact change. All crawlers see this HTML before any JS executes.

- [ ] **Step 1: Replace the current `<head>` content**

```html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="theme-color" content="#0d1117" />

    <!-- Primary Meta -->
    <title>Wildfire Insight Intelligence — Satellite-Powered Fire Damage Assessment</title>
    <meta name="description" content="Turn satellite data into actionable wildfire intelligence. Assess burn severity, map fire damage, and generate scientific reports from Sentinel-2 imagery — in seconds." />
    <meta name="keywords" content="wildfire assessment, burn severity, fire damage, satellite imagery, Sentinel-2, post-fire analysis, dNBR, remote sensing, wildfire intelligence, fire management" />
    <meta name="author" content="Brazil Flying Labs" />

    <!-- Canonical -->
    <link rel="canonical" href="https://wildfire.droneai.com.br/" />

    <!-- Open Graph -->
    <meta property="og:type" content="website" />
    <meta property="og:site_name" content="Wildfire Insight Intelligence" />
    <meta property="og:title" content="Wildfire Insight Intelligence — Satellite-Powered Fire Damage Assessment" />
    <meta property="og:description" content="Turn satellite data into actionable wildfire intelligence. Assess burn severity, map fire damage, and generate scientific reports from Sentinel-2 imagery — in seconds." />
    <meta property="og:url" content="https://wildfire.droneai.com.br/" />
    <meta property="og:image" content="https://wildfire.droneai.com.br/front-end-screenshot.png" />
    <meta property="og:image:width" content="1200" />
    <meta property="og:image:height" content="630" />
    <meta property="og:locale" content="en_US" />
    <meta property="og:locale:alternate" content="pt_BR" />
    <meta property="og:locale:alternate" content="es_ES" />
    <meta property="og:locale:alternate" content="fr_FR" />

    <!-- Twitter Card -->
    <meta name="twitter:card" content="summary_large_image" />
    <meta name="twitter:title" content="Wildfire Insight Intelligence — Satellite-Powered Fire Damage Assessment" />
    <meta name="twitter:description" content="Turn satellite data into actionable wildfire intelligence. Assess burn severity, map fire damage, and generate scientific reports from Sentinel-2 imagery." />
    <meta name="twitter:image" content="https://wildfire.droneai.com.br/front-end-screenshot.png" />

    <!-- Hreflang (single URL, language selection is client-side) -->
    <link rel="alternate" hreflang="en" href="https://wildfire.droneai.com.br/" />
    <link rel="alternate" hreflang="pt-BR" href="https://wildfire.droneai.com.br/" />
    <link rel="alternate" hreflang="es" href="https://wildfire.droneai.com.br/" />
    <link rel="alternate" hreflang="fr" href="https://wildfire.droneai.com.br/" />
    <link rel="alternate" hreflang="x-default" href="https://wildfire.droneai.com.br/" />

    <!-- Favicons -->
    <link rel="icon" type="image/x-icon" href="%PUBLIC_URL%/favicon.ico" />
    <link rel="icon" type="image/png" sizes="16x16" href="%PUBLIC_URL%/favicon-16x16.png" />
    <link rel="icon" type="image/png" sizes="32x32" href="%PUBLIC_URL%/favicon-32x32.png" />
    <link rel="apple-touch-icon" sizes="180x180" href="%PUBLIC_URL%/apple-touch-icon.png" />
    <link rel="manifest" href="%PUBLIC_URL%/webmanifest" />

    <!-- Structured Data (Organization + WebApplication) -->
    <script type="application/ld+json">
    {
      "@context": "https://schema.org",
      "@graph": [
        {
          "@type": "Organization",
          "@id": "https://wildfire.droneai.com.br/#organization",
          "name": "Brazil Flying Labs",
          "url": "https://wildfire.droneai.com.br",
          "logo": {
            "@type": "ImageObject",
            "url": "https://wildfire.droneai.com.br/logo.png"
          },
          "email": "humanos@brazilflyinglabs.org.br",
          "sameAs": []
        },
        {
          "@type": "WebApplication",
          "@id": "https://wildfire.droneai.com.br/#application",
          "name": "Wildfire Insight Intelligence",
          "url": "https://wildfire.droneai.com.br",
          "description": "A data-driven platform that transforms satellite data into clear, standardized wildfire intelligence. Calculates burned area, classifies fire severity, maps spatial distribution, and generates georeferenced scientific outputs.",
          "applicationCategory": "EnvironmentalScience",
          "operatingSystem": "Web Browser",
          "offers": {
            "@type": "Offer",
            "price": "0",
            "priceCurrency": "USD"
          },
          "provider": {
            "@type": "Organization",
            "@id": "https://wildfire.droneai.com.br/#organization"
          },
          "featureList": [
            "Burned area calculation from Sentinel-2 imagery",
            "Fire severity classification (dNBR, RBR, dNDVI)",
            "Spatial distribution mapping",
            "Georeferenced scientific deliverables (GeoTIFF)",
            "AI-powered fire impact analysis",
            "Multi-language support (English, Portuguese, Spanish, French)"
          ],
          "screenshot": "https://wildfire.droneai.com.br/front-end-screenshot.png",
          "inLanguage": ["en", "pt-BR", "es-ES", "fr"]
        },
        {
          "@type": "WebPage",
          "@id": "https://wildfire.droneai.com.br/#webpage",
          "url": "https://wildfire.droneai.com.br/",
          "name": "Wildfire Insight Intelligence — Satellite-Powered Fire Damage Assessment",
          "description": "Turn satellite data into actionable wildfire intelligence. Assess burn severity, map fire damage, and generate scientific reports from Sentinel-2 imagery — in seconds.",
          "isPartOf": {
            "@type": "WebSite",
            "@id": "https://wildfire.droneai.com.br/#website",
            "name": "Wildfire Insight Intelligence",
            "url": "https://wildfire.droneai.com.br"
          },
          "about": {
            "@type": "WebApplication",
            "@id": "https://wildfire.droneai.com.br/#application"
          },
          "provider": {
            "@type": "Organization",
            "@id": "https://wildfire.droneai.com.br/#organization"
          }
        }
      ]
    }
    </script>

    <!-- Preconnects -->
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link
      href="https://fonts.googleapis.com/css2?family=Mona+Sans:wght@400;500;600;700&display=swap"
      rel="stylesheet"
    />
    <link
      rel="stylesheet"
      href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css"
    />
  </head>
  <body>
    <noscript>You need to enable JavaScript to run this app.</noscript>
    <div id="root"></div>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
  </body>
</html>
```

Key changes:
- Title: `"Wildfire Insight Intelligence — Satellite-Powered Fire Damage Assessment"` (keyword-rich, under 60 chars visible in SERP)
- Description: Action-oriented, 155 chars, includes key terms (satellite, burn severity, Sentinel-2)
- Full Open Graph tags with image (reuses existing `front-end-screenshot.png`)
- Twitter large image card
- Canonical URL to production domain
- Hreflang for all 4 languages + x-default
- JSON-LD structured data: Organization + WebApplication + WebPage graph
- Proper favicon chain
- Theme color matches landing page dark theme (`#0d1117`)
- Preconnects before stylesheet loads (performance)

- [ ] **Step 2: Verify structured data**

After build, paste the HTML into Google's Rich Results Test (https://search.google.com/test/rich-results) and Schema Markup Validator (https://validator.schema.org/).

- [ ] **Step 3: Commit**

```bash
git add ui/public/index.html
git commit -m "feat(seo): optimize meta tags, OG, Twitter cards, structured data, hreflang"
```

---

## Task 2: Create OG Image (1200x630)

**Files:**
- Create: `ui/public/og-image.png` (1200x630 optimized for social sharing)

The existing `front-end-screenshot.png` may not be optimized for OG image dimensions (1200x630). A dedicated OG image should include:
- Platform name "Wildfire Insight Intelligence"
- Brazil Flying Labs logo
- A visual of the platform UI or a satellite fire map
- Dark background matching the landing page theme

- [ ] **Step 1: Check current screenshot dimensions**

```bash
identify ui/public/front-end-screenshot.png  # or use file/sips
```

If it's not 1200x630, create a purpose-built OG image. Tools: Figma, Canva, or programmatically with Sharp/Canvas.

- [ ] **Step 2: Update meta tags to use dedicated OG image if created**

Replace `front-end-screenshot.png` with `og-image.png` in the og:image and twitter:image meta tags.

- [ ] **Step 3: Commit**

```bash
git add ui/public/og-image.png ui/public/index.html
git commit -m "feat(seo): add dedicated OG social sharing image"
```

---

## Task 3: Create `sitemap.xml`

**Files:**
- Create: `ui/public/sitemap.xml`

Only 2 public pages exist. Keep it simple.

- [ ] **Step 1: Create the sitemap**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:xhtml="http://www.w3.org/1999/xhtml">
  <url>
    <loc>https://wildfire.droneai.com.br/</loc>
    <lastmod>2026-03-24</lastmod>
    <changefreq>monthly</changefreq>
    <priority>1.0</priority>
    <xhtml:link rel="alternate" hreflang="en" href="https://wildfire.droneai.com.br/" />
    <xhtml:link rel="alternate" hreflang="pt-BR" href="https://wildfire.droneai.com.br/" />
    <xhtml:link rel="alternate" hreflang="es" href="https://wildfire.droneai.com.br/" />
    <xhtml:link rel="alternate" hreflang="fr" href="https://wildfire.droneai.com.br/" />
    <xhtml:link rel="alternate" hreflang="x-default" href="https://wildfire.droneai.com.br/" />
  </url>
  <url>
    <loc>https://wildfire.droneai.com.br/privacy</loc>
    <lastmod>2026-03-13</lastmod>
    <changefreq>yearly</changefreq>
    <priority>0.3</priority>
  </url>
</urlset>
```

- [ ] **Step 2: Commit**

```bash
git add ui/public/sitemap.xml
git commit -m "feat(seo): add sitemap.xml with landing page and privacy policy"
```

---

## Task 4: Update `robots.txt`

**Files:**
- Modify: `ui/public/robots.txt`

- [ ] **Step 1: Replace robots.txt**

```
User-agent: *
Allow: /
Disallow: /dashboard
Disallow: /analysis
Disallow: /areas
Disallow: /profile

Sitemap: https://wildfire.droneai.com.br/sitemap.xml
```

This tells crawlers to index `/` and `/privacy` but skip authenticated app routes (even though they'd hit a login wall anyway, this prevents wasted crawl budget and "soft 404" signals).

- [ ] **Step 2: Commit**

```bash
git add ui/public/robots.txt
git commit -m "feat(seo): update robots.txt with sitemap ref and app route exclusions"
```

---

## Task 5: Fix Web App Manifest

**Files:**
- Modify: `ui/public/webmanifest`

- [ ] **Step 1: Update manifest**

```json
{
  "name": "Wildfire Insight Intelligence",
  "short_name": "Wildfire",
  "description": "Satellite-powered wildfire damage assessment platform",
  "start_url": "/",
  "display": "standalone",
  "theme_color": "#0d1117",
  "background_color": "#0d1117",
  "icons": [
    { "src": "/favicon-16x16.png", "sizes": "16x16", "type": "image/png" },
    { "src": "/favicon-32x32.png", "sizes": "32x32", "type": "image/png" },
    { "src": "/android-chrome-192x192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/android-chrome-512x512.png", "sizes": "512x512", "type": "image/png" }
  ]
}
```

- [ ] **Step 2: Commit**

```bash
git add ui/public/webmanifest
git commit -m "fix(seo): populate web manifest with proper name, theme, and icons"
```

---

## Task 6: Dynamic `<html lang>` Attribute

**Files:**
- Modify: `ui/src/context/LanguageContext.js` (or wherever the language effect lives)

Google uses the `<html lang>` attribute as a ranking signal. Currently hardcoded to `"en"` in index.html. It should update dynamically when the user selects a language.

- [ ] **Step 1: Find where language is set**

Check `LanguageContext.js` for the language change handler.

- [ ] **Step 2: Add a `useEffect` to sync `<html lang>`**

In the LanguageContext provider (or in App.js), add:

```javascript
useEffect(() => {
  document.documentElement.lang = language; // e.g., "en", "pt-BR", "es-ES", "fr"
}, [language]);
```

This ensures crawlers that execute JS see the correct language attribute.

- [ ] **Step 3: Commit**

```bash
git add ui/src/context/LanguageContext.js
git commit -m "feat(seo): sync html lang attribute with selected language"
```

---

## Task 7: Add `llms.txt` for AI Search Readiness

**Files:**
- Create: `ui/public/llms.txt`

AI search engines (ChatGPT, Perplexity, Claude) look for `llms.txt` to understand what a site offers.

- [ ] **Step 1: Create llms.txt**

```
# Wildfire Insight Intelligence
> A data-driven platform by Brazil Flying Labs that transforms satellite data into actionable wildfire intelligence.

## What It Does
- Calculates burned area extent from Sentinel-2 satellite imagery
- Classifies fire severity using dNBR, RBR, and dNDVI indices
- Maps spatial distribution of fire damage
- Generates georeferenced scientific deliverables (GeoTIFF)
- Produces AI-powered fire impact analysis reports

## Who It Serves
Environmental agencies, local governments, climate resilience programs, and organizations managing forested and natural landscapes.

## Deployments
Active pilots with Fundação Florestal (São Paulo, Brazil) and Flying Labs in Bolivia, Cameroon, Malaysia, Morocco, Mozambique, Nepal, and Sierra Leone.

## Technology
Built on Google Earth Engine, Sentinel-2 imagery, and scientifically validated burn severity algorithms. No advanced remote sensing expertise required.

## Access
Free platform. Requires authentication. Request access at humanos@brazilflyinglabs.org.br

## Links
- Platform: https://wildfire.droneai.com.br
- Privacy Policy: https://wildfire.droneai.com.br/privacy
```

- [ ] **Step 2: Commit**

```bash
git add ui/public/llms.txt
git commit -m "feat(seo): add llms.txt for AI search engine readiness"
```

---

## Task 8: Landing Page Noscript Fallback

**Files:**
- Modify: `ui/public/index.html`

For crawlers that don't execute JavaScript, the `<noscript>` block is all they see. Replace the generic message with SEO-rich content.

- [ ] **Step 1: Replace noscript content**

```html
<noscript>
  <h1>Wildfire Insight Intelligence</h1>
  <p>Turn satellite data into actionable wildfire intelligence. Wildfire Insight Intelligence is a data-driven platform by Brazil Flying Labs that automatically calculates burned area, classifies fire severity, maps spatial distribution, and generates georeferenced scientific outputs from Sentinel-2 satellite imagery.</p>
  <p>Active in Brazil, Bolivia, Cameroon, Malaysia, Morocco, Mozambique, Nepal, and Sierra Leone.</p>
  <p>Contact: <a href="mailto:humanos@brazilflyinglabs.org.br">humanos@brazilflyinglabs.org.br</a></p>
</noscript>
```

This gives non-JS crawlers meaningful content to index.

- [ ] **Step 2: Commit**

```bash
git add ui/public/index.html
git commit -m "feat(seo): add rich noscript fallback for non-JS crawlers"
```

---

## Future Considerations (Not in Scope Now)

### Language-Specific URLs (Phase 2)
The biggest SEO limitation is that all 4 languages share one URL (`/`). For serious multilingual SEO:
- Add route prefixes: `/en/`, `/pt-br/`, `/es/`, `/fr/`
- Each gets its own canonical and hreflang
- Google can rank different language versions for different markets

This requires a routing refactor and is a separate project.

### Pre-rendering (Phase 2)
Consider `react-snap` or a pre-rendering service to generate static HTML snapshots of the landing page. This would give crawlers the full rendered content without needing JS execution. Google handles JS well, but Bing, Yandex, and AI crawlers are less reliable.

### Blog / Content Marketing (Phase 3)
A `/blog` with articles about wildfire management, burn severity analysis, and remote sensing would build topical authority and drive organic traffic. This is a significant effort but high-impact for long-term SEO.

### Google Search Console
After deploying these changes:
1. Verify the site in Google Search Console
2. Submit the sitemap
3. Request indexing of the landing page
4. Monitor Core Web Vitals and indexing status

---

## Target Keywords

| Keyword | Search Volume | Difficulty | Relevance |
|---------|--------------|------------|-----------|
| wildfire assessment | Medium | Medium | Primary |
| burn severity mapping | Low | Low | Primary |
| post-fire analysis tool | Low | Low | Primary |
| satellite fire damage assessment | Low | Low | Primary |
| wildfire intelligence platform | Low | Low | Primary |
| dNBR fire severity | Low | Low | Secondary |
| Sentinel-2 fire analysis | Low | Low | Secondary |
| wildfire damage satellite | Medium | Medium | Secondary |
| avaliação de incêndios florestais | Low (pt-BR) | Low | Primary (Brazil) |
| análise de severidade de queimadas | Low (pt-BR) | Low | Primary (Brazil) |

The niche is specialized enough that proper technical SEO + good content will rank well without aggressive link building.

---

## Implementation Order

| Task | Impact | Effort | Priority |
|------|--------|--------|----------|
| 1. Meta tags + structured data | HIGH | LOW | Do first |
| 3. Sitemap | MEDIUM | VERY LOW | Do first |
| 4. Robots.txt | MEDIUM | VERY LOW | Do first |
| 5. Web manifest | LOW | VERY LOW | Do first |
| 6. Dynamic html lang | MEDIUM | LOW | Do first |
| 8. Noscript fallback | MEDIUM | LOW | Do first |
| 7. llms.txt | LOW | VERY LOW | Do first |
| 2. OG image | MEDIUM | MEDIUM | Do when ready |

Tasks 1, 3, 4, 5, 6, 7, 8 can all be done in one session. Task 2 (OG image) depends on whether the existing screenshot works at 1200x630.
