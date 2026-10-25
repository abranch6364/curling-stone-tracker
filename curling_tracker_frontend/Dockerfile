ARG NODE_VERSION=24.7.0-alpine

# Builds the frontend into static files for the web stage
FROM node:${NODE_VERSION} AS curling-frontend-build

WORKDIR /app

COPY package.json package-lock.json ./

RUN --mount=type=cache,target=/root/.npm npm ci

COPY . .

RUN npm run build

# Serves the built frontend and passes /api to the backend, with HTTPS for a domain, built with --target
# curling-frontend-web. See the Caddyfile.
FROM caddy:2-alpine AS curling-frontend-web

COPY Caddyfile /etc/caddy/Caddyfile
COPY --from=curling-frontend-build /app/build /srv

# The development server. It's the last stage, so it's what's built without a --target.
FROM node:${NODE_VERSION} AS curling-frontend-dev

WORKDIR /app

COPY package.json package-lock.json ./

RUN --mount=type=cache,target=/root/.npm npm install

COPY . .

EXPOSE 3000

CMD ["npm", "start"]