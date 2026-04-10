#!/bin/bash
set -e

echo "🚀 Starting Gerador de Relatórios Kiro..."

# Check required environment variables
if [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ ERROR: OPENAI_API_KEY is not set"
    exit 1
fi

# Set default values
export STORAGE_TYPE=${STORAGE_TYPE:-"local"}
export STORAGE_LOCAL_PATH=${STORAGE_LOCAL_PATH:-"/app/uploads"}
export LOG_LEVEL=${LOG_LEVEL:-"INFO"}
export ENVIRONMENT=${ENVIRONMENT:-"production"}

# Create necessary directories
mkdir -p /app/uploads /app/exports /app/reports /app/logs

# Set permissions
chmod -R 755 /app/uploads /app/exports /app/reports /app/logs

echo "✅ Environment configured"
echo "   - Storage: ${STORAGE_TYPE}"
echo "   - Log Level: ${LOG_LEVEL}"
echo "   - Environment: ${ENVIRONMENT}"

# Start supervisor (manages nginx + backend)
echo "🎯 Starting services..."
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
