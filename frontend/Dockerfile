# Boussole frontend image.
#
# Next.js 15 with the server runtime. Built in three stages so the runtime
# image carries only the .next/standalone output and the public/ assets.
#
# Build:
#   docker build -f frontend/Dockerfile -t boussole-frontend:dev frontend
# Run:
#   docker run --rm -p 3000:3000 \
#     -e BOUSSOLE_API_ORIGIN=https://api.boussole.example boussole-frontend:dev

ARG NODE_VERSION=22

FROM node:${NODE_VERSION}-bookworm-slim AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

FROM node:${NODE_VERSION}-bookworm-slim AS builder
ENV NEXT_TELEMETRY_DISABLED=1
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# Force the standalone output so the runtime image stays small.
RUN sed -i 's|outputFileTracingRoot:.*|outputFileTracingRoot: path.join(__dirname),\n  output: "standalone",|' next.config.ts \
 || true
RUN npm run build

FROM node:${NODE_VERSION}-bookworm-slim AS runtime
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0

WORKDIR /app

RUN groupadd -r boussole && useradd -r -g boussole -d /app -s /sbin/nologin boussole

COPY --from=builder --chown=boussole:boussole /app/.next/standalone ./
COPY --from=builder --chown=boussole:boussole /app/.next/static ./.next/static
COPY --from=builder --chown=boussole:boussole /app/public ./public

USER boussole

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD node -e "require('http').get('http://127.0.0.1:3000/',res=>process.exit(res.statusCode<500?0:1)).on('error',()=>process.exit(1))"

CMD ["node", "server.js"]
