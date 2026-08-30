# External Services

All third-party services and platforms used by the Wildfire Insight
Intelligence project.

## Infrastructure

| Service | URL | Description |
|---------|-----|-------------|
| **Contabo** | [Console](https://contabo.com/) | Dedicated VPS (Debian 12) hosting the Docker Compose stack |
| **Cloudflare** | [Dashboard](https://dash.cloudflare.com/) | DNS for `wildfire.droneai.com.br` and `api.wildfire.droneai.com.br` |
| **Nginx Proxy Manager** | VPS `127.0.0.1:81` | Reverse proxy, TLS (Let's Encrypt), proxy hosts for UI and API |

## Storage & Satellite Analysis

| Service | URL | Description |
|---------|-----|-------------|
| **Google Earth Engine** | [Platform](https://earthengine.google.com/) | Satellite imagery processing — Sentinel-2 data for burn severity analysis (dNBR, RBR, dNDVI, RGB) |
| **Google Cloud Storage** | [Console](https://console.cloud.google.com/storage) | `wildfire-assessment-assets` (app polygons and images) and `wildfire-analyser-outputs` (scientific deliverables) |

## AI

| Service | URL | Description |
|---------|-----|-------------|
| **DeepSeek** | [Platform](https://platform.deepseek.com/) | Active AI provider (text-only) for analysis reports and chat follow-ups, model `deepseek-chat` |
| **OpenAI** | [API](https://platform.openai.com/) | Prepared provider (image-aware) for future use |
| **Google Gemini** | [API](https://ai.google.dev/) | Prepared provider (image-aware) for future use |

## E-mail

| Service | URL | Description |
|---------|-----|-------------|
| **Docker Mailserver** | `mail.droneai.com.br` | SMTP (STARTTLS, port 587) with a dedicated project account |
