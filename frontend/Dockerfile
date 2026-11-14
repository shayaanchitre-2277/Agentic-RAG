# ==============================================================================
# Frontend Dockerfile for Agentic RAG Vite + React
# Multi-stage Node 20 Build + Nginx Alpine Runtime
# ==============================================================================

# --- Stage 1: Build static assets ---
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies using package-lock.json
COPY package*.json ./
RUN npm ci

# Copy application source
COPY . .

# Build arguments for Vite client environment
ARG VITE_SUPABASE_URL=http://127.0.0.1:54321
ARG VITE_SUPABASE_ANON_KEY=placeholder-local-anon-key
ARG VITE_API_BASE_URL=http://127.0.0.1:8000

ENV VITE_SUPABASE_URL=$VITE_SUPABASE_URL \
    VITE_SUPABASE_ANON_KEY=$VITE_SUPABASE_ANON_KEY \
    VITE_API_BASE_URL=$VITE_API_BASE_URL

RUN npm run build

# --- Stage 2: Serve via Nginx ---
FROM nginx:alpine AS runner

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

