# Gerador de Relatórios Kiro

Sistema profissional de análise documental e geração de relatórios especializados utilizando arquitetura multiagente com LangGraph.

## 🎯 Visão Geral

Aplicação web completa para upload, análise e geração de relatórios técnicos a partir de documentos em múltiplos formatos. Utiliza agentes especializados com IA para produzir relatórios de alta qualidade com revisão editorial automatizada.

### Características Principais

- ✅ Upload de documentos (.pdf, .docx, .xlsx, .csv, .txt, .pptx, .md)
- ✅ Análise automática de conteúdo
- ✅ 6 tipos de relatórios especializados
- ✅ Arquitetura multiagente com LangGraph
- ✅ **Seleção inteligente de modelo LLM** (MiniMax M2.5 grátis + GPT-4o)
- ✅ Revisão editorial automatizada
- ✅ Exportação em MD, PDF e DOCX
- ✅ Segurança contra prompt injection
- ✅ Interface moderna com dark mode
- ✅ Testes automatizados completos

## 📋 Tipos de Relatórios

1. **Resumo Analítico** - Síntese executiva do conteúdo
2. **Relatório Técnico** - Análise técnica detalhada
3. **Relatório FINEP** - Formato para agências de fomento
4. **Parecer Técnico** - Avaliação técnica fundamentada
5. **Relato Científico** - Formato científico estruturado
6. **Documento Acadêmico** - Estrutura de dissertação/tese

## 🏗️ Arquitetura

### Stack Tecnológico

**Backend:**

- Python 3.11+
- FastAPI
- LangGraph (orquestração multiagente)
- LangChain + OpenAI
- PostgreSQL
- Redis
- SQLAlchemy
- Pydantic v2

**Frontend:**

- React 18
- TypeScript
- Vite
- Tailwind CSS
- shadcn/ui
- React Query
- Zustand

**Infraestrutura:**

- Docker & Docker Compose
- Nginx
- OpenTelemetry (observabilidade)

### Arquitetura Multiagente

```
Supervisor Agent (coordenador)
    ├── Ingestion Parser Agent (parsing)
    ├── Security Guard Agent (segurança)
    ├── Analysis Summary Agent (análise)
    ├── Specialist Report Agents (geração)
    │   ├── Technical Report Agent
    │   ├── FINEP Report Agent
    │   ├── Technical Opinion Agent
    │   ├── Scientific Report Agent
    │   └── Academic Longform Agent
    ├── Review Editor Agent (revisão)
    └── Export Agent (exportação)
```

## 🚀 Início Rápido

### Deploy no EasyPanel (Recomendado)

A forma mais rápida de colocar em produção:

1. **Fork/Clone o repositório**
2. **Configure no EasyPanel:**
   - Conecte seu repositório GitHub
   - Configure variáveis de ambiente (OPENAI_API_KEY, etc)
   - Deploy automático!

Veja o [guia completo de deploy no EasyPanel](docs/deployment/EASYPANEL_DEPLOY.md).

### Pré-requisitos

- Docker e Docker Compose
- Python 3.11+ (para desenvolvimento local)
- Node.js 18+ (para desenvolvimento local)
- Chave API da OpenAI

### Instalação com Docker

1. Clone o repositório:

```bash
git clone https://github.com/SEU_USUARIO/gerador_relatorio_kiro.git
cd gerador_relatorio_kiro
```

2. Configure as variáveis de ambiente:

```bash
cp .env.example .env
# Edite .env e adicione:
# - OPENAI_API_KEY (obrigatório)
# - MINIMAX_API_KEY (opcional, para modelo gratuito)
```

3. Inicie os serviços:

```bash
docker-compose up -d
```

4. Acesse a aplicação:

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Instalação Local (Desenvolvimento)

**Backend:**

```bash
cd apps/backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp ../../.env.example .env
# Configure .env com suas credenciais
uvicorn src.api.main:app --reload
```

**Frontend:**

```bash
cd apps/frontend
npm install
cp ../../.env.example .env.local
# Configure .env.local
npm run dev
```

## 🎯 Otimização de Custos

### Seleção Inteligente de Modelos

O sistema escolhe automaticamente entre dois modelos baseado na complexidade da tarefa:

**MiniMax M2.5 (Gratuito)** para:

- Parsing de documentos
- Análise de segurança
- Supervisão de workflow
- Exportação

**GPT-4o (Premium)** para:

- Geração de relatórios
- Revisão editorial
- Análise profunda

**Economia estimada:** ~60% em custos de API vs. usar apenas GPT-4o

Veja [documentação completa](docs/MODEL_SELECTION.md) para detalhes.

## 📖 Uso

1. **Upload**: Arraste ou selecione um documento
2. **Análise**: Aguarde a análise automática do conteúdo
3. **Tipo**: Selecione o tipo de relatório desejado
4. **Geração**: Clique em "Gerar Relatório"
5. **Revisão**: O sistema revisa automaticamente
6. **Edição**: Edite o relatório se necessário
7. **Exportação**: Baixe em MD, PDF ou DOCX

## 🔒 Segurança

### Proteções Implementadas

- ✅ Validação de MIME type e magic bytes
- ✅ Detecção de prompt injection
- ✅ Detecção de prompt hiding
- ✅ Sanitização de entrada e saída
- ✅ Rate limiting
- ✅ Autenticação JWT
- ✅ RBAC (Role-Based Access Control)
- ✅ Auditoria completa
- ✅ Validação de schema (Pydantic)

### Defesa em Profundidade

```
Input → Validation → Guard Agent → Processing → Output Sanitization → User
```

## 🧪 Testes

### Executar Todos os Testes

```bash
cd apps/backend
pytest
```

### Testes por Categoria

```bash
# Testes unitários
pytest src/tests/unit/

# Testes de integração
pytest src/tests/integration/

# Testes de segurança
pytest src/tests/security/

# Testes E2E
pytest src/tests/e2e/

# Com cobertura
pytest --cov=src --cov-report=html
```

## 📊 Observabilidade

### Logs Estruturados

Todos os logs são estruturados em JSON para fácil parsing:

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "info",
  "event": "report_generated",
  "document_id": "abc123",
  "report_type": "technical_report",
  "duration_ms": 5420
}
```

### Métricas

- Tempo de processamento por etapa
- Taxa de sucesso/falha
- Qualidade dos relatórios (score)
- Detecções de segurança

## 🛠️ Desenvolvimento

### Estrutura do Projeto

```
gerador_relatorio_kiro/
├── apps/
│   ├── backend/          # API FastAPI + LangGraph
│   └── frontend/         # React + TypeScript
├── packages/
│   ├── prompts/          # Prompts dos agentes
│   └── shared-types/     # Tipos compartilhados
├── infra/
│   └── docker/           # Dockerfiles
├── docs/                 # Documentação
└── tests/                # Testes E2E
```

### Qualidade de Código

```bash
# Formatação
black apps/backend/src
ruff check apps/backend/src

# Type checking
mypy apps/backend/src

# Pre-commit hooks
pre-commit install
pre-commit run --all-files
```

## 📚 Documentação

- [Arquitetura](docs/architecture/README.md)
- [Seleção de Modelos](docs/MODEL_SELECTION.md)
- [API Reference](docs/api/README.md)
- [Segurança](docs/security/README.md)
- [Testes](docs/testing/README.md)
- [ADRs](docs/adr/README.md)

## 🤝 Contribuindo

1. Fork o projeto
2. Crie uma branch (`git checkout -b feature/nova-funcionalidade`)
3. Commit suas mudanças (`git commit -m 'feat: adiciona nova funcionalidade'`)
4. Push para a branch (`git push origin feature/nova-funcionalidade`)
5. Abra um Pull Request

### Conventional Commits

Usamos [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` Nova funcionalidade
- `fix:` Correção de bug
- `docs:` Documentação
- `test:` Testes
- `refactor:` Refatoração
- `chore:` Manutenção

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

## 👥 Autores

- Desenvolvido com Kiro AI

## 🙏 Agradecimentos

- LangChain e LangGraph pela framework multiagente
- OpenAI pela API de LLM
- Comunidade open source

## 📞 Suporte

- Issues: [GitHub Issues](https://github.com/SEU_USUARIO/gerador_relatorio_kiro/issues)
- Documentação: [Wiki](https://github.com/SEU_USUARIO/gerador_relatorio_kiro/wiki)

---

**Status do Projeto:** 🚧 Em Desenvolvimento Ativo

**Versão:** 1.0.0

**Última Atualização:** 2024
