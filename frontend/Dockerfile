# =============================================================================
# EBA Frontend — Dockerfile
# Multi-stage: development | production
# =============================================================================

# ---------------------------------------------------------------------------
# Stage: base
# ---------------------------------------------------------------------------
FROM node:22-alpine AS base

LABEL maintainer="EBA Team"
LABEL description="Enterprise Billing Automation — Frontend"

WORKDIR /app

# ---------------------------------------------------------------------------
# Stage: development — Vite dev server com hot-reload
# ---------------------------------------------------------------------------
FROM base AS development

COPY package.json package-lock.json* ./

RUN npm ci

COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host"]

# ---------------------------------------------------------------------------
# Stage: builder — compila a aplicação
# ---------------------------------------------------------------------------
FROM base AS builder

COPY package.json package-lock.json* ./
RUN npm ci --only=production=false

COPY . .
RUN npm run build

# ---------------------------------------------------------------------------
# Stage: production — serve com Nginx
# ---------------------------------------------------------------------------
FROM nginx:1.27-alpine AS production

# Configuração do Nginx
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -qO- http://localhost/health || exit 1

CMD ["nginx", "-g", "daemon off;"]

