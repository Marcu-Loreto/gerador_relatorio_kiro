#!/bin/bash
set -e

echo "🐳 Testing Docker build for EasyPanel..."

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${RED}❌ .env file not found${NC}"
    echo "Creating from .env.example..."
    cp .env.example .env
    echo -e "${YELLOW}⚠️  Please edit .env and add your API keys${NC}"
    exit 1
fi

# Check if OPENAI_API_KEY is set
if ! grep -q "OPENAI_API_KEY=sk-" .env; then
    echo -e "${RED}❌ OPENAI_API_KEY not configured in .env${NC}"
    exit 1
fi

echo -e "${GREEN}✓${NC} Environment file found"

# Build the image
echo ""
echo "📦 Building Docker image..."
docker build -t gerador-relatorio-kiro:test -f Dockerfile .

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} Docker image built successfully"
else
    echo -e "${RED}❌ Docker build failed${NC}"
    exit 1
fi

# Test run
echo ""
echo "🚀 Starting container for testing..."
docker run -d \
    --name gerador-relatorio-test \
    -p 8080:80 \
    --env-file .env \
    gerador-relatorio-kiro:test

# Wait for container to be ready
echo ""
echo "⏳ Waiting for application to start..."
sleep 10

# Health check
echo ""
echo "🏥 Running health check..."
for i in {1..30}; do
    if curl -f http://localhost:8080/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Health check passed!"
        break
    fi
    
    if [ $i -eq 30 ]; then
        echo -e "${RED}❌ Health check failed after 30 attempts${NC}"
        echo ""
        echo "Container logs:"
        docker logs gerador-relatorio-test
        docker stop gerador-relatorio-test
        docker rm gerador-relatorio-test
        exit 1
    fi
    
    echo "Attempt $i/30..."
    sleep 2
done

# Test endpoints
echo ""
echo "🧪 Testing endpoints..."

# Test root
if curl -f http://localhost:8080/ > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Frontend accessible"
else
    echo -e "${YELLOW}⚠${NC}  Frontend not accessible (may be normal if not built)"
fi

# Test API
if curl -f http://localhost:8080/api/v1 > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} API accessible"
else
    echo -e "${YELLOW}⚠${NC}  API returned error (may need authentication)"
fi

# Test docs
if curl -f http://localhost:8080/docs > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} API docs accessible"
else
    echo -e "${YELLOW}⚠${NC}  API docs not accessible"
fi

# Show container info
echo ""
echo "📊 Container information:"
docker stats gerador-relatorio-test --no-stream

# Cleanup
echo ""
echo "🧹 Cleaning up..."
docker stop gerador-relatorio-test
docker rm gerador-relatorio-test

echo ""
echo -e "${GREEN}✅ Docker test completed successfully!${NC}"
echo ""
echo "To run the container manually:"
echo "  docker run -d -p 8080:80 --env-file .env gerador-relatorio-kiro:test"
echo ""
echo "To push to registry:"
echo "  docker tag gerador-relatorio-kiro:test your-registry/gerador-relatorio-kiro:latest"
echo "  docker push your-registry/gerador-relatorio-kiro:latest"
echo ""
