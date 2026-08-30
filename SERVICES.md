# External Services

All third-party services and platforms used by the Wildfire Insight Intelligence project.

## Core Infrastructure

| Service | URL | Description |
|---------|-----|-------------|
| **AWS** | [Console](https://055213706289.signin.aws.amazon.com/console) | Cloud infrastructure — ECS (containers), RDS Aurora (PostgreSQL + PostGIS), S3 (storage), CloudFront (CDN), ALB, ECR, Secrets Manager, CloudWatch |
| **GitHub Actions** | [Workflows](https://github.com/Brazil-Flying-Labs/wildfire-assessment/actions) | CI/CD — API deployment to ECS, UI deployment to S3/CloudFront, Terraform automation |

## Authentication

| Service | URL | Description |
|---------|-----|-------------|
| **Auth0** | [Dashboard](https://manage.auth0.com/) | User authentication and JWT token management for both web and mobile apps |

## Observability & Analytics

| Service | URL | Description |
|---------|-----|-------------|
| **Grafana Cloud** | [Dashboard](https://brazilflyinglabs.grafana.net/) | Monitoring, alerting, and dashboards — Prometheus (metrics), Loki (logs), Faro (frontend error tracking and RUM), Alloy (OpenTelemetry collector) |
| **PostHog** | [Dashboard](https://us.posthog.com/project/322814/) | Product analytics and user behavior tracking for the web app |

## AI & Satellite Analysis

| Service | URL | Description |
|---------|-----|-------------|
| **Google Earth Engine** | [Platform](https://earthengine.google.com/) | Satellite imagery processing — Sentinel-2 data for burn severity analysis (dNBR, RBR, dNDVI, RGB) |
| **Google Gemini** | [API](https://ai.google.dev/) | Default AI provider for wildfire analysis reports and follow-up Q&A (model: `gemini-2.0-flash-lite`) |
| **OpenAI** | [API](https://platform.openai.com/) | Alternative AI provider for analysis reports (model: `gpt-4o-mini`) |

## Mobile

| Service | URL | Description |
|---------|-----|-------------|
| **Expo** | [Dashboard](https://expo.dev/accounts/brazil-flying-labs/) | React Native build platform, OTA updates, and push notification delivery via Expo Push Service |

## Email

| Service | URL | Description |
|---------|-----|-------------|
