# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Wildfire damage assessment platform: Django REST API + React UI + Celery workers, using satellite imagery (GEE) to analyze burn severity. Deployed on AWS (ECS, S3, CloudFront, RDS). Auth via Auth0 JWT tokens.

## Architecture

```
api/wildfire_assessment/     Django app (models, views, serializers, svc/)
  svc/                       Service layer: aws.py, processor.py, dashboard.py, ai_analysis.py, analytics.py
  tests/                     Django TestCase tests (not pytest)
ui/src/                      React 19 SPA (Auth0, Leaflet maps, Recharts)
iac/                         Terraform (ECS, RDS, S3, CloudFront, ALB)
```

Six Docker services: `wildfire-api` (Django), `wildfire-ui` (React), `wildfire-db` (PostGIS), `wildfire-celery`, `wildfire-celery-beat`, `wildfire-redis`.

The API container mounts `./api:/api` so local edits are hot-reloaded. Tests run inside the container against SQLite in-memory (test_settings.py).

## General Rules

If any change/addition on backend code, we should write/fix unit tests until the coverage is 100%. This is MANDATORY. No exceptions. If you add a new function, you must add tests for it. If you change existing code, you must ensure all tests pass and coverage is maintained. If coverage drops, you must add tests to bring it back up. This is critical for maintaining code quality and preventing regressions. Always run tests and check coverage before pushing code. Always run the full test suite after making changes, not just the tests you think are affected. This ensures we catch any unintended consequences. If you see a test failure, investigate and fix it before proceeding. Never ignore failing tests or push code with known test failures. This is non-negotiable.

## Commands

### Start/stop services

```bash
make up                    # docker compose up
make reset                 # full clean rebuild
make do_stop               # kill all wildfire containers
```

### Run tests (Django TestCase, not pytest)

```bash
# Full suite with coverage (inside Docker)
docker exec wildfire-api bash -c "coverage run --source=wildfire_assessment manage.py test && coverage report"

# Single test class or method
docker exec wildfire-api python manage.py test wildfire_assessment.tests.test_services.DashboardServiceTests
docker exec wildfire-api python manage.py test wildfire_assessment.tests.test_services.DashboardServiceTests.test_severity_trend

# Via Makefile (uses docker compose exec)
make test
```

### Frontend

```bash
docker exec wildfire-ui npm start    # already running via compose
docker exec wildfire-ui npm run build
docker exec wildfire-ui npm test
```

### Django management

```bash
docker exec wildfire-api python manage.py migrate
docker exec wildfire-api python manage.py createsuperuser
docker exec wildfire-api python manage.py makemigrations wildfire_assessment
```

### Code quality (run locally in venv, enforced via pre-commit)

```bash
black api svc --config pyproject.toml
isort api svc --profile black
flake8 api svc
```

## Key Patterns

- **Service layer** (`svc/`): Business logic lives here, not in views or serializers. Views call services; serializers handle validation and S3 uploads.
- **Auth**: `Auth0JWTAuthentication` in authentication.py validates JWT, auto-creates inactive Django users on first request. All endpoints require `IsAuthenticated`.
- **Country-based access control**: Users are authorized per-country via `UserCountry`. Serializers validate country access on create/update.
- **Async processing**: Fire assessments run via Celery tasks (`processor.py`). Scientific deliverables track GEE task IDs in `AnalysisRun` and poll for completion.
- **GeoJSON handling**: Polygon files stored in S3 (`polygons/` prefix). Serializers validate GeoJSON structure, coordinate bounds, and geometry validity (shapely).
- **Test settings**: `api/api/test_settings.py` uses SQLite in-memory, disabled migrations, MD5 hasher, and `SKIP_AWS_SECRETS=1`. All AWS/S3 calls must be mocked in tests.
- **Coverage**: Target is 100%. Coverage config: `--source=wildfire_assessment`.

## Environment

- `.env` file required (see `.env.template`). Set `SKIP_AWS_SECRETS=1` for local dev.
- Python 3.13, Node 18, PostgreSQL 15 + PostGIS 3.3.
- `pyproject.toml`: Black line-length 88, isort profile "black".
- `.flake8`: max-line-length 88, ignores E203/E501.

## CI/CD

- **API**: Push to `dev` triggers test + deploy to ECS (`ecs-workflow.yml`).
- **UI**: Push to `dev` triggers build + S3 sync + CloudFront invalidation (`ui-deploy.yml`).
- Tests must pass before deploy. Coverage report generated in CI.
