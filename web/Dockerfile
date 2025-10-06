# Stage 1: Build React app with Vite
FROM node:22-bookworm AS build
WORKDIR /app

# Debian/glibc base avoids musl-specific Rollup binary resolution issues

# Install dependencies
COPY package.json package-lock.json ./
RUN npm ci

# Copy source
COPY . .

# Accept build-time env for Vite
ARG VITE_API_URL=http://localhost:8000
ARG VITE_SUPABASE_URL
ARG VITE_SUPABASE_ANON_KEY

# Generate .env.production for Vite build
RUN printf "VITE_API_URL=%s\nVITE_SUPABASE_URL=%s\nVITE_SUPABASE_ANON_KEY=%s\n" \
  "$VITE_API_URL" "$VITE_SUPABASE_URL" "$VITE_SUPABASE_ANON_KEY" > .env.production

# Build static assets
RUN npm run build

# Stage 2: Serve with Nginx
FROM nginx:alpine AS runtime
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

# No CMD override; use Nginx default