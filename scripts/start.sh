#!/bin/bash
# Inicia backend e frontend em paralelo para testes de usuário

set -e

# Cores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Gerador de Relatórios Kiro - START   ${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Verificar .venv
if [ ! -f ".venv/bin/python" ]; then
    echo -e "${YELLOW}⚠  Ambiente virtual não encontrado. Criando...${NC}"
    uv venv
    uv sync
fi

# Verificar node_modules do frontend
if [ ! -d "apps/frontend/node_modules" ]; then
    echo -e "${YELLOW}⚠  Dependências do frontend não encontradas. Instalando...${NC}"
    npm install --prefix apps/frontend
fi

# Criar diretórios necessários
mkdir -p uploads exports logs

# Cleanup ao sair
cleanup() {
    echo ""
    echo -e "${YELLOW}Encerrando serviços...${NC}"
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    exit 0
}
trap cleanup SIGINT SIGTERM

# Iniciar backend
echo -e "${BLUE}[BACKEND]${NC} Iniciando em http://localhost:8000 ..."
PYTHONPATH="$ROOT_DIR/apps/backend" \
    "$ROOT_DIR/.venv/bin/python" -m uvicorn src.api.main:app \
    --host 0.0.0.0 --port 8000 --reload \
    2>&1 | sed 's/^/[BACKEND] /' &
BACKEND_PID=$!

# Aguardar backend subir
echo -e "${BLUE}[BACKEND]${NC} Aguardando inicialização..."
for i in {1..20}; do
    if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}[BACKEND]${NC} ✓ Rodando em http://localhost:8000"
        echo -e "${GREEN}[BACKEND]${NC} ✓ Swagger UI: http://localhost:8000/docs"
        break
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
echo -e "  Credenciais de teste:"
echo -e "    admin / admin123"
echo -e "    user  / user123"
echo ""
echo -e "  Pressione ${YELLOW}Ctrl+C${NC} para encerrar"
echo ""

# Aguardar
wait $BACKEND_PID $FRONTEND_PID
