# ── Stage 1: build the React app ─────────────────────────────────
FROM node:18-alpine AS builder

WORKDIR /ui

# Dependencies are installed at build time (npm ci), never at startup.
COPY ui/package.json ui/package-lock.json ./
RUN npm ci

COPY ui/ ./

# Public configuration only — never secrets.
ARG REACT_APP_WILDLIFE_API_URL
ARG REACT_APP_APP_ENVIRONMENT
ENV REACT_APP_WILDLIFE_API_URL=${REACT_APP_WILDLIFE_API_URL} \
    REACT_APP_APP_ENVIRONMENT=${REACT_APP_APP_ENVIRONMENT}

RUN npm run build

# ── Stage 2: serve the static build with nginx ───────────────────
FROM nginx:alpine

COPY --from=builder /ui/build /usr/share/nginx/html
COPY ui/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
