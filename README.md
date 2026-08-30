# Wildfire Insight Intelligence

AI-assisted assessment and classification of fire damage caused by wildfires,
using satellite imagery (Sentinel-2 via Google Earth Engine) to analyze burn
severity.

Stack: Django REST API + React SPA + Celery worker + PostgreSQL + Redis,
running on Docker Compose. Deployed on a Contabo VPS behind an existing
Nginx Proxy Manager. Storage on Google Cloud Storage; AI analysis via
DeepSeek (text-only).

## Quick start (local)

Requirements: Docker Engine + Docker Compose plugin.

1. Create the environment file:

   ```bash
   cp .env.example .env
   # fill in DJANGO_SECRET_KEY, DB_* and the GCP values
   ```

2. Place the Google service account credential at
   `secrets/gcp-service-account.json` (gitignored). The same service account
   is used by Google Earth Engine and Google Cloud Storage.

3. Start the stack:

   ```bash
   make up        # or: docker compose up -d
   ```

4. Create the first administrator:

   ```bash
   docker compose exec -e DJANGO_SUPERUSER_USERNAME=admin \
     -e DJANGO_SUPERUSER_EMAIL=you@example.com \
     -e DJANGO_SUPERUSER_PASSWORD=your-password \
     api python manage.py createsuperuser --noinput
   ```

Direct access: UI at http://localhost:3000, API at http://localhost:8081,
Django Admin at http://localhost:8081/admin/.

### Optional: local Nginx Proxy Manager

Reproduces the VPS access shape (`wildfire.droneai.test` /
`api.wildfire.droneai.test`):

```bash
docker network create proxy_network
docker compose -f compose.yml -f compose.override.yml -f compose.npm.yml \
  --profile proxy up -d
# /etc/hosts: 127.0.0.1 wildfire.droneai.test api.wildfire.droneai.test
```

NPM admin at http://127.0.0.1:8181 (first login forces a password change).
Create the proxy hosts via the NPM API — see `MIGRATION_PLAN.md` (Fase 7).

## Tests

```bash
make test      # backend: Django TestCase, SQLite in-memory, 100% coverage
make test_ui   # frontend: react-scripts test
```

## Configuration

See `.env.example` for every supported variable. Required: `DJANGO_SECRET_KEY`,
`DB_NAME`, `DB_USERNAME`, `DB_PASSWORD`, `DB_HOST`. Optional AI providers:
`OPENAI_API_KEY`, `GEMINI_API_KEY`, `DEEPSEEK_API_KEY` (the V1 uses DeepSeek,
text-only). GCS defaults: `GCS_BUCKET_NAME=wildfire-analyser-outputs`
(scientific) and `GCS_APP_BUCKET_NAME=wildfire-assessment-assets` (app
polygons/images), prefix `GCS_APP_PREFIX=dev`.

## GCP setup (one time)

- Service account registered in Earth Engine, key downloaded to
  `secrets/gcp-service-account.json`.
- App bucket with public access prevention enforced and `Storage Object
  Admin` for the service account.
- Pin: `earthengine-api==1.7.1` (newer versions break service-account auth).

## Production (Contabo VPS)

See `MIGRATION_PLAN.md` for the full plan. In short: clone the repo, create
the production `.env` and the GCP credential (chown the file to the container
user, e.g. `chown 10001:10001 secrets/gcp-service-account.json`), build the
images, run migrations, create the superuser, and publish UI/API through the
existing Nginx Proxy Manager (no host ports).
