# Multi-stage Dockerfile for EasyPanel deployment
# Optimized for production with both frontend and backend

# ============================================
# Stage 1: Build Frontend
# ============================================
FROM node:18-alpine AS frontend-builder

WORKDIR /frontend

# Copy frontend package files
COPY apps/frontend/package*.json ./

# Install dependencies including devDependencies required for build
RUN npm ci

# Copy frontend source
COPY apps/frontend/ ./

# Build frontend for production
RUN npm run build

# ============================================
# Stage 2: Build Backend
# ============================================
FROM python:3.11-slim AS backend-builder

WORKDIR /backend

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements
COPY apps/backend/requirements.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# ============================================
# Stage 3: Production Runtime
# ============================================
FROM python:3.11-slim AS runtime

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000 \
    HOST=0.0.0.0 \
    PATH=/root/.local/bin:$PATH

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libmagic1 \
    curl \
    nginx \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=backend-builder /root/.local /root/.local

# Copy backend application
COPY apps/backend/ ./backend/

# Copy built frontend from builder
COPY --from=frontend-builder /frontend/dist ./frontend/dist/

# Copy shared packages
COPY packages/ ./packages/

# Create necessary directories
RUN mkdir -p /app/uploads /app/exports /app/logs /var/log/supervisor

# Copy nginx configuration
COPY infra/easypanel/nginx.conf /etc/nginx/nginx.conf

# Copy supervisor configuration
COPY infra/easypanel/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Copy startup script
COPY infra/easypanel/start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Expose port used by EasyPanel
EXPOSE 8000

# Start application
CMD ["/app/start.sh"]