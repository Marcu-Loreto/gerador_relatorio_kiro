#!/bin/bash
# Inicia backend e frontend em paralelo para testes de usuário

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Gerador de Relatórios Kiro - START   ${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Verificar .venv
if [ ! -f ".venv/bin/python" ]; then
    echo -e "${RED}✗ Ambiente virtual não encontrado em .venv/${NC}"
    echo -e "  Execute: python3 -m venv .venv && source .venv/bin/activate && pip install -r apps/backend/requirements.txt"
    exit 1
fi

PYTHON="$ROOT_DIR/.venv/bin/python"

# Verificar OPENAI_API_KEY
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | grep -v '^\s*$' | xargs) 2>/dev/null || true
fi

if [ -z "$OPENAI_API_KEY" ]; then
    echo -e "${RED}✗ OPENAI_API_KEY não definida no .env${NC}"
    exit 1
fi

# Verificar node_modules do frontend
if [ ! -d "apps/frontend/node_modules" ]; then
    echo -e "${YELLOW}⚠  Instalando dependências do frontend...${NC}"
    npm install --prefix apps/frontend --silent
fi

# Criar diretórios necessários
mkdir -p uploads exports logs reports

# Liberar portas se ocupadas
fuser -k 8000/tcp 2>/dev/null || true
fuser -k 5173/tcp 2>/dev/null || true
sleep 1

# Cleanup ao sair
cleanup() {
    echo ""
    echo -e "${YELLOW}Encerrando serviços...${NC}"
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
    exit 0
}
trap cleanup SIGINT SIGTERM

# Iniciar backend
echo -e "${BLUE}[BACKEND]${NC} Iniciando em http://localhost:8000 ..."
PYTHONPATH="$ROOT_DIR/apps/backend" \
    "$PYTHON" -m uvicorn src.api.main:app \
    --host 0.0.0.0 --port 8000 --reload \
    2>&1 | sed 's/^/[BACKEND] /' &
BACKEND_PID=$!

# Aguardar backend subir (até 30s)
echo -e "${BLUE}[BACKEND]${NC} Aguardando inicialização..."
for i in {1..30}; do
    if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}[BACKEND]${NC} ✓ http://localhost:8000"
        break
    fi
    if ! kill -0 $BACKEND_PID 2>/dev/null; then
        echo -e "${RED}[BACKEND]${NC} ✗ Processo encerrou inesperadamente"
        exit 1
    fi
    sleep 1
done

# Iniciar frontend
echo -e "${GREEN}[FRONTEND]${NC} Iniciando em http://localhost:5173 ..."
npm run dev --prefix "$ROOT_DIR/apps/frontend" \
    2>&1 | sed 's/^/[FRONTEND] /' &
FRONTEND_PID=$!

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Aplicação rodando!                   ${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "  Frontend:  ${GREEN}http://localhost:5173${NC}"
echo -e "  Backend:   ${BLUE}http://localhost:8000${NC}"
echo -e "  API Docs:  ${BLUE}http://localhost:8000/docs${NC}"
echo ""
echo -e "  Pressione ${YELLOW}Ctrl+C${NC} para encerrar"
echo ""

wait $BACKEND_PID $FRONTEND_PID
