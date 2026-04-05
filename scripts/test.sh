#!/bin/bash
set -e

echo "🧪 Running tests for Gerador de Relatórios Kiro..."

cd apps/backend

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

echo "📦 Installing test dependencies..."
pip install -q -r requirements.txt

echo ""
echo "🔍 Running linters..."
echo "  - Ruff..."
ruff check src/ || true

echo "  - Black (check only)..."
black --check src/ || true

echo "  - MyPy..."
mypy src/ || true

echo ""
echo "🧪 Running unit tests..."
pytest src/tests/unit/ -v

echo ""
echo "🔗 Running integration tests..."
pytest src/tests/integration/ -v || true

echo ""
echo "🔒 Running security tests..."
pytest src/tests/security/ -v

echo ""
echo "📊 Generating coverage report..."
pytest --cov=src --cov-report=html --cov-report=term-missing

echo ""
echo "✅ Tests complete!"
echo "📄 Coverage report: apps/backend/htmlcov/index.html"
