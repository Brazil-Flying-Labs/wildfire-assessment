# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Wildfire damage assessment platform: Django REST API + React UI + Celery worker, using satellite imagery (GEE) to analyze burn severity. Runs on Docker Compose (local and on a Contabo VPS behind an existing Nginx Proxy Manager). Storage on Google Cloud Storage. Native session authentication (e-mail/password, admin approval); AI analysis via DeepSeek (text-only).

## Architecture

```
api/wildfire_assessment/     Django app (models, views, serializers, svc/)
  svc/                       Service layer: processor.py, dashboard.py, ai_analysis (ai_common, deepseek/openai/gemini), object_storage.py, analytics.py
  tests/                     Django TestCase tests (not pytest)
ui/src/                      React 19 SPA (Leaflet maps, Recharts)
compose*.yml                 Docker Compose (base, dev override, prod, local NPM profile)
```

Five Docker services: `api` (Django), `ui` (React; dev serves via react-scripts, prod via nginx), `postgres` (PostgreSQL 16), `redis`, `celery-worker`. The VPS's Nginx Proxy Manager is not part of this Compose; `api` and `ui` join the external `proxy_network`.

The API container mounts `./api:/api` so local edits are hot-reloaded. Tests run inside the container against SQLite in-memory (`api.test_settings`).

## General Rules

1. If any change/addition on backend code, we should write/fix unit tests until the coverage is 100%. This is MANDATORY. No exceptions. If you add a new function, you must add tests for it. If you change existing code, you must ensure all tests pass and coverage is maintained. If coverage drops, you must add tests to bring it back up. This is critical for maintaining code quality and preventing regressions. Always run tests and check coverage before pushing code. Always run the full test suite after making changes, not just the tests you think are affected. This ensures we catch any unintended consequences. If you see a test failure, investigate and fix it before proceeding. Never ignore failing tests or push code with known test failures. This is non-negotiable. Deployments with less than 100% coverage will be rejected because it is mandatory to be 100% covered to ensure code quality and reliability. Never PUSH without running tests and checking coverage. Always ensure tests pass and coverage is 100% before pushing code.

2. Keep the codebase DRY (Don't Repeat Yourself). If you find yourself copying and pasting code, consider refactoring to create reusable functions or classes. This applies to both backend and frontend code. For example, if you have similar logic for handling GCS uploads in multiple places, consider creating a utility function in `object_storage.py` that can be reused across serializers or services.

3. When writing code respect the black instructions on the pyproject.toml file. This ensures consistent code formatting across the codebase. Black will be run automatically on pre-commit, but you should also run it manually before pushing code to ensure everything is formatted correctly. You can run `black api svc --config pyproject.toml` to format the backend code. For the frontend, you can run `npm run format` inside the `ui` container to format the React code.

4. NEVER, NEVER add ORM logic on the view. The correct place for ORM logic is the service layer (svc/). Views should only handle request parsing, authentication, and calling the appropriate service functions. All business logic, including database queries, should be encapsulated in the service layer. This separation of concerns makes the code more maintainable and testable. If you find yourself writing ORM queries in a view, stop and refactor that code into a service function instead.

5. if anything changes on our terms and services we need to update TERMS_LAST_UPDATED settings so the users will be forced to accept the new terms and conditions.

6. Never push code without EXPLICITLY asked by me. Always wait for my instructions before pushing code to the repository. This is important to ensure that all changes are coordinated and reviewed properly. If you have made changes and are ready to push, please notify me and wait for my confirmation before proceeding. This allows me to review the changes, run tests, and ensure that everything is in order before the code is merged into the main branch. Always communicate with me before pushing code to maintain a smooth workflow and avoid any potential issues.

7. VERY IMPORTANT: Every new change/addition on the Web App must also be made on the Mobile App and the Electron App. Also the opposite, every change on the Mobile App/Electron App must also be made on the Web App. We need to keep all the three platforms in sync to provide a consistent user experience. If you add a new feature or make a change on the Web App, you must also implement that change on the Mobile App and the elctron app. Similarly, if you make a change on the Mobile App, you must ensure that the same change is reflected on the Web App and the electron app. If you make a change on the elctron app you must ensure the same change is reflected on the Web App/Mobile app. This is crucial for maintaining feature parity and ensuring that users have a seamless experience across both platforms. Always check for any changes made on either platform and ensure they are implemented on the other as well.

### Where are the repos?
WEB - /Users/diogo/github-archive/repos/Brazil-Flying-Labs/wildfire-assessment
MOBILE APP = /Users/diogo/github-archive/repos/Brazil-Flying-Labs/wildfire-assessment-app
ELECTRON APP = /Users/diogo/github-archive/repos/Brazil-Flying-Labs/wildfire-assessment-electron

## Commands

### Start/stop services

```bash
make up                    # docker compose up -d (dev, direct ports)
make up_proxy              # same, with the local Nginx Proxy Manager profile
make down / restart / logs / ps / build
make clean                 # down -v (removes the database volume — destructive)
```

Always use the full `-f` chain when running the proxy profile manually:

```bash
docker compose -f compose.yml -f compose.override.yml -f compose.npm.yml --profile proxy up -d
```

⚠️ Recreating services without the `compose.npm.yml` file detaches `api`/`ui`
from `proxy_network` and breaks the proxy flow.

### Run tests (Django TestCase, not pytest)

```bash
make test   # full suite with coverage (SQLite in-memory, api.test_settings)
make test_ui
```

The suite MUST run with `DJANGO_SETTINGS_MODULE=api.test_settings`; running
with `api.settings` produces false failures (Postgres, real throttle rates,
AI disabled).

### Frontend

```bash
docker compose exec ui npm test -- --watchAll=false --ci
docker compose exec ui npm run build
```

### Django management

```bash
docker compose exec api python manage.py migrate
docker compose exec api python manage.py createsuperuser
docker compose exec api python manage.py makemigrations wildfire_assessment
```

## Key Patterns

- **Service layer** (`svc/`): Business logic lives here, not in views or serializers. Views call services; serializers handle validation and GCS uploads.
- **Auth**: native session authentication (e-mail/password). Public flow: request access → admin approval (Django Admin action "Approve and send first-password link") → single-use set-password link → login. All endpoints require `IsAuthenticated` except the auth endpoints. CSRF: the UI caches the token returned by `/auth/csrf/` (the cookie is unreadable cross-subdomain through the proxy).
- **Country-based access control**: Users are authorized per-country via `UserCountry`; serializers validate country access on create/update. Grant countries in the Django Admin (user page).
- **Async processing**: scientific deliverables run via Celery tasks (`processor.py`); `AnalysisRun` tracks GEE task IDs and polling.
- **GeoJSON handling**: Polygon files stored in GCS (`dev/polygons/` prefix) via `svc/object_storage.py`. Serializers validate GeoJSON structure, coordinate bounds, geometry validity (shapely), part area ≥ 10 m², total area ≤ 110,000 ha.
- **AI**: provider dispatch in `svc/ai_common.py`; singleton `AIProvider` (gemini/openai/deepseek). DeepSeek is text-only — prompts use `include_images=False` and the report skips image downloads.
- **Migrations**: single squashed `0001_initial` + subsequent numbered migrations. On fresh installs the DB is built from models state.
- **Test settings**: `api/api/test_settings.py` uses SQLite in-memory, disabled migrations, MD5 hasher. All GCS/GEE/network calls must be mocked in tests.
- **Coverage**: Target is 100%. Coverage config: `--source=wildfire_assessment`.

## Environment

- `.env` file required (see `.env.example`). `secrets/gcp-service-account.json` holds the GEE/GCS service-account key (gitignored, mounted read-only at `/run/secrets/gcp-service-account.json`).
- Python 3.13, Node 18, PostgreSQL 16.
- `pyproject.toml`: Black line-length 88, isort profile "black".
- `.flake8`: max-line-length 88, ignores E203/E501.

## CI/CD

No automatic deploys in the V1: deploys are manual on the VPS (build images, migrate, restart Compose). Tests must pass and coverage stay at 100% before any push.

## TRACK DEPLOYMENTS

- Every time you push changes to dev/staging/prod branches, track the deployments, one background agent for each deployment and notify me with a sound when deployments are ready.
