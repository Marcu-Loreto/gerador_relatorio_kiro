#!/bin/bash
set -e

echo "🚀 Starting Gerador de Relatórios Kiro..."

# Check required environment variables
if [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ ERROR: OPENAI_API_KEY is not set"
    exit 1
fi

# Set default values for optional variables
export DATABASE_URL=${DATABASE_URL:-"sqlite:///./app.db"}
export REDIS_URL=${REDIS_URL:-"redis://localhost:6379/0"}
export STORAGE_TYPE=${STORAGE_TYPE:-"local"}
export STORAGE_LOCAL_PATH=${STORAGE_LOCAL_PATH:-"/app/uploads"}
export LOG_LEVEL=${LOG_LEVEL:-"INFO"}
export ENVIRONMENT=${ENVIRONMENT:-"production"}

# Create necessary directories
mkdir -p /app/uploads /app/exports /app/logs

# Set permissions
chmod -R 755 /app/uploads /app/exports /app/logs

echo "✅ Environment configured"
echo "   - Database: ${DATABASE_URL}"
echo "   - Redis: ${REDIS_URL}"
echo "   - Storage: ${STORAGE_TYPE}"
echo "   - Log Level: ${LOG_LEVEL}"
echo "   - Environment: ${ENVIRONMENT}"

# Run database migrations if needed
if [ "$RUN_MIGRATIONS" = "true" ]; then
    echo "🔄 Running database migrations..."
    cd /app/backend
    # alembic upgrade head || echo "⚠️  Migrations failed or not configured"
    cd /app
fi

# Start supervisor (manages nginx + backend)
echo "🎯 Starting services..."
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
