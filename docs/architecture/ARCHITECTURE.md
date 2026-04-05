# Arquitetura do Sistema

## Visão Geral

O Gerador de Relatórios Kiro é um sistema distribuído baseado em microserviços que utiliza arquitetura multiagente para processamento inteligente de documentos.

## Princípios Arquiteturais

### 1. Separação de Responsabilidades

- Frontend: Apresentação e interação do usuário
- Backend: Lógica de negócio e orquestração
- Agentes: Tarefas especializadas de IA
- Infraestrutura: Persistência e serviços auxiliares

### 2. Clean Architecture

```
┌─────────────────────────────────────┐
│         API Layer (FastAPI)         │
├─────────────────────────────────────┤
│    Application Layer (Use Cases)    │
├─────────────────────────────────────┤
│   Domain Layer (Business Logic)     │
├─────────────────────────────────────┤
│  Infrastructure (DB, Storage, etc)  │
└─────────────────────────────────────┘
```

### 3. Defesa em Profundidade

Múltiplas camadas de segurança:

- Validação de entrada
- Guard agent dedicado
- Sanitização de saída
- Auditoria completa

## Componentes Principais

### Frontend (React + TypeScript)

**Responsabilidades:**

- Interface do usuário
- Upload de arquivos
- Visualização e edição de relatórios
- Feedback de progresso em tempo real

**Tecnologias:**

- React 18 com hooks
- TypeScript para type safety
- Tailwind CSS para estilização
- React Query para gerenciamento de estado servidor
- Zustand para estado local

### Backend (FastAPI + Python)

**Responsabilidades:**

- API REST
- Autenticação e autorização
- Orquestração de agentes
- Persistência de dados
- Gerenciamento de arquivos

**Camadas:**

1. **API Layer** (`src/api/`)
   - Rotas HTTP
   - Validação de requisições
   - Serialização de respostas
   - Middleware de segurança

2. **Application Layer** (`src/application/`)
   - Use cases
   - Services
   - DTOs (Data Transfer Objects)
   - Orquestração de fluxos

3. **Domain Layer** (`src/domain/`)
   - Entidades de negócio
   - Value objects
   - Interfaces de repositórios
   - Regras de negócio

4. **Infrastructure Layer** (`src/infrastructure/`)
   - Implementação de repositórios
   - Acesso a banco de dados
   - Storage de arquivos
   - Cache (Redis)
   - Observabilidade

### Sistema Multiagente (LangGraph)

**Arquitetura:**

```
                    ┌──────────────┐
                    │  Supervisor  │
                    │    Agent     │
                    └──────┬───────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
   ┌────▼────┐      ┌─────▼──────┐    ┌─────▼──────┐
   │ Parser  │      │  Security  │    │  Analysis  │
   │  Agent  │      │    Guard   │    │   Agent    │
   └─────────┘      └────────────┘    └────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
   ┌────▼────┐      ┌─────▼──────┐    ┌─────▼──────┐
   │Technical│      │   FINEP    │    │ Scientific │
   │ Report  │      │   Report   │    │   Report   │
   └────┬────┘      └─────┬──────┘    └─────┬──────┘
        │                  │                  │
        └──────────────────┼──────────────────┘
                           │
                    ┌──────▼───────┐
                    │    Review    │
                    │    Editor    │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │    Export    │
                    │    Agent     │
                    └──────────────┘
```

**Agentes Especializados:**

1. **Supervisor Agent**
   - Coordena o fluxo de trabalho
   - Toma decisões de roteamento
   - Gerencia retries e erros
   - Nunca gera conteúdo

2. **Ingestion Parser Agent**
   - Detecta tipo de arquivo
   - Extrai conteúdo
   - Normaliza estrutura
   - Gera metadados

3. **Security Guard Agent**
   - Detecta prompt injection
   - Identifica conteúdo malicioso
   - Bloqueia ou sinaliza riscos
   - Sanitiza quando necessário

4. **Analysis Summary Agent**
   - Compreende o documento
   - Extrai tópicos principais
   - Identifica contexto e objetivos
   - Gera resumo analítico

5. **Specialist Report Agents**
   - Technical Report Agent
   - FINEP Report Agent
   - Technical Opinion Agent
   - Scientific Report Agent
   - Academic Longform Agent
   - Cada um especializado em seu formato

6. **Review Editor Agent**
   - Revisa qualidade
   - Valida aderência ao formato
   - Identifica inconsistências
   - Aprova ou solicita revisão

7. **Export Agent**
   - Converte para Markdown
   - Gera PDF
   - Gera DOCX
   - Preserva formatação

## Fluxo de Dados

### 1. Upload e Parsing

```
User → Frontend → API → Validation → Storage → Parser Agent → State
```

### 2. Análise e Segurança

```
State → Security Guard → Analysis Agent → State Update
```

### 3. Geração de Relatório

```
State → Supervisor → Specialist Agent → Report → State
```

### 4. Revisão e Exportação

```
Report → Review Agent → Approved? → Export Agent → Files
                      ↓ Rejected
                   Revision Loop
```

## Persistência

### PostgreSQL

- Usuários e autenticação
- Metadados de documentos
- Histórico de relatórios
- Auditoria

### Redis

- Cache de sessões
- Cache de análises
- Fila de jobs
- Rate limiting

### File Storage

- Documentos originais
- Relatórios gerados
- Exports (MD, PDF, DOCX)
- Suporte a S3 ou filesystem local

## Segurança

### Camadas de Proteção

1. **Input Validation**
   - MIME type checking
   - File size limits
   - Extension whitelist
   - Path traversal prevention

2. **Guard Agent**
   - Prompt injection detection
   - Malicious content scanning
   - Risk scoring
   - Blocking/sanitization

3. **Output Sanitization**
   - Markdown sanitization
   - HTML escaping
   - Script removal

4. **Authentication & Authorization**
   - JWT tokens
   - RBAC
   - Session management
   - Rate limiting

5. **Audit Trail**
   - All actions logged
   - Security events tracked
   - Compliance reporting

## Observabilidade

### Logging

- Structured JSON logs
- Correlation IDs
- Log levels (DEBUG, INFO, WARNING, ERROR)
- Centralized aggregation

### Metrics

- Request latency
- Success/failure rates
- Agent execution times
- Resource utilization

### Tracing

- OpenTelemetry integration
- Distributed tracing
- Span annotations
- Performance profiling

## Escalabilidade

### Horizontal Scaling

- Stateless API servers
- Load balancing
- Session affinity via Redis
- Database connection pooling

### Vertical Scaling

- Resource limits configuráveis
- Memory management
- Connection pooling
- Cache optimization

### Async Processing

- Background jobs para tarefas longas
- Webhook notifications
- Polling endpoints para status

## Decisões Arquiteturais (ADRs)

Ver pasta `docs/adr/` para decisões arquiteturais documentadas:

- ADR-001: Escolha do LangGraph
- ADR-002: Arquitetura multiagente
- ADR-003: Estratégia de segurança
- ADR-004: Formato de exportação

## Diagramas

### Diagrama de Componentes

```
┌─────────────────────────────────────────────────┐
│                   Frontend                       │
│  (React + TypeScript + Tailwind)                │
└────────────────┬────────────────────────────────┘
                 │ HTTPS/REST
┌────────────────▼────────────────────────────────┐
│              API Gateway                         │
│         (FastAPI + Middleware)                   │
└────────────────┬────────────────────────────────┘
                 │
    ┌────────────┼────────────┐
    │            │            │
┌───▼───┐  ┌────▼────┐  ┌───▼────┐
│ Auth  │  │Document │  │ Report │
│Service│  │ Service │  │Service │
└───┬───┘  └────┬────┘  └───┬────┘
    │           │            │
    └───────────┼────────────┘
                │
    ┌───────────▼────────────┐
    │   LangGraph Engine     │
    │  (Multi-Agent System)  │
    └───────────┬────────────┘
                │
    ┌───────────┼────────────┐
    │           │            │
┌───▼────┐ ┌───▼────┐  ┌───▼────┐
│Postgres│ │ Redis  │  │Storage │
└────────┘ └────────┘  └────────┘
```

## Considerações de Produção

### Performance

- Cache agressivo de análises
- Lazy loading de documentos
- Streaming de respostas longas
- CDN para assets estáticos

### Reliability

- Health checks
- Graceful shutdown
- Circuit breakers
- Retry policies

### Monitoring

- Application metrics
- Infrastructure metrics
- Business metrics
- Alerting

### Backup & Recovery

- Database backups diários
- File storage replication
- Disaster recovery plan
- RTO/RPO definidos
