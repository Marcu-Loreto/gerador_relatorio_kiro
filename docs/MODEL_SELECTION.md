# Sistema de Seleção Inteligente de Modelos

## Visão Geral

O Gerador de Relatórios Kiro implementa um sistema inteligente de seleção de modelos LLM que escolhe automaticamente entre diferentes modelos baseado na complexidade da tarefa, otimizando custos sem comprometer qualidade.

## Modelos Disponíveis

### MiniMax M2.5 (Gratuito)

- **Provider:** MiniMax
- **Custo:** Gratuito
- **Uso:** Tarefas simples e moderadas
- **Características:**
  - Parsing de documentos
  - Análise básica
  - Supervisão de workflow
  - Tarefas de roteamento

### GPT-4o (Premium)

- **Provider:** OpenAI
- **Custo:** Premium
- **Uso:** Tarefas complexas
- **Características:**
  - Geração de relatórios
  - Revisão editorial
  - Análise profunda
  - Copywriting técnico

## Estratégias de Seleção

### 1. Auto (Padrão)

Seleciona automaticamente o modelo baseado na complexidade da tarefa e do conteúdo.

```bash
MODEL_SELECTION_STRATEGY=auto
```

**Lógica de Decisão:**

- Analisa o tipo de tarefa
- Avalia o tamanho do conteúdo
- Considera a complexidade estrutural
- Escolhe o modelo mais adequado

### 2. Simple

Força o uso do modelo simples (MiniMax) para todas as tarefas.

```bash
MODEL_SELECTION_STRATEGY=simple
```

**Quando usar:**

- Ambiente de desenvolvimento
- Testes
- Orçamento limitado
- Documentos simples

### 3. Complex

Força o uso do modelo complexo (GPT-4o) para todas as tarefas.

```bash
MODEL_SELECTION_STRATEGY=complex
```

**Quando usar:**

- Máxima qualidade necessária
- Documentos críticos
- Produção com SLA rigoroso

### 4. Modelo Específico

Especifica um modelo exato para usar.

```bash
MODEL_SELECTION_STRATEGY=gpt-4-turbo-preview
```

## Mapeamento de Tarefas

### Tarefas Simples (MiniMax M2.5)

| Tarefa        | Complexidade | Justificativa                 |
| ------------- | ------------ | ----------------------------- |
| Parsing       | Simples      | Extração estruturada de dados |
| Security Scan | Simples      | Pattern matching e regras     |
| Supervision   | Simples      | Roteamento baseado em regras  |
| Export        | Simples      | Conversão de formato          |

**Tokens:** 2048 max  
**Temperatura:** 0.3  
**Custo:** $0

### Tarefas Complexas (GPT-4o)

| Tarefa            | Complexidade | Justificativa                |
| ----------------- | ------------ | ---------------------------- |
| Report Generation | Complexa     | Criação de conteúdo original |
| Review            | Complexa     | Análise crítica e editorial  |
| Deep Analysis     | Complexa     | Compreensão profunda         |

**Tokens:** 8192 max  
**Temperatura:** 0.3  
**Custo:** Variável por uso

### Tarefas Moderadas (Adaptativo)

| Tarefa        | Complexidade | Modelo Usado       |
| ------------- | ------------ | ------------------ |
| Analysis      | Moderada     | MiniMax (padrão)   |
| Summarization | Moderada     | Baseado no tamanho |

## Análise de Complexidade de Conteúdo

O sistema analisa o conteúdo para ajustar a complexidade:

### Fatores Considerados

1. **Tamanho do Conteúdo**
   - < 500 palavras: Pode downgrade
   - 500-5000 palavras: Mantém base
   - > 5000 palavras: Pode upgrade

2. **Tipo de Tarefa**
   - Parsing: Sempre simples
   - Geração: Sempre complexa
   - Análise: Adaptativo

3. **Estrutura**
   - Texto simples: Simples
   - Múltiplas seções: Moderado
   - Tabelas e dados: Complexo

### Exemplos

```python
# Documento curto + análise = Simples
content = "Breve descrição do projeto..."  # 100 palavras
task = TaskType.ANALYSIS
# Resultado: MiniMax M2.5

# Documento longo + geração = Complexo
content = "Documento técnico extenso..."  # 10000 palavras
task = TaskType.REPORT_GENERATION
# Resultado: GPT-4o

# Documento médio + revisão = Complexo
content = "Relatório para revisar..."  # 2000 palavras
task = TaskType.REVIEW
# Resultado: GPT-4o (revisão sempre complexa)
```

## Configuração

### Variáveis de Ambiente

```bash
# Chaves de API
OPENAI_API_KEY=sk-...
MINIMAX_API_KEY=...  # Opcional, fallback para OpenAI se ausente

# Estratégia
MODEL_SELECTION_STRATEGY=auto  # auto, simple, complex, ou nome do modelo

# Modelos
SIMPLE_MODEL=minimax-m2.5
COMPLEX_MODEL=gpt-4o

# Parâmetros
DEFAULT_TEMPERATURE=0.3
DEFAULT_MAX_TOKENS=4096
SIMPLE_TASK_MAX_TOKENS=2048
COMPLEX_TASK_MAX_TOKENS=8192
```

### Fallback Automático

Se a chave do MiniMax não estiver configurada:

```
MiniMax solicitado → Chave ausente → Fallback para GPT-4o
```

## Uso Programático

### Obter LLM para uma Tarefa

```python
from src.core.model_selector import TaskType, get_model_selector

selector = get_model_selector()

# Seleção automática
llm = selector.get_llm(
    task_type=TaskType.REPORT_GENERATION,
    content=document_content,
)

# Forçar complexidade
llm = selector.get_llm(
    task_type=TaskType.ANALYSIS,
    force_complexity=TaskComplexity.COMPLEX,
)

# Parâmetros customizados
llm = selector.get_llm(
    task_type=TaskType.REVIEW,
    temperature=0.1,
    max_tokens=4096,
)
```

### Verificar Modelo Selecionado

```python
model_name = selector.select_model(
    task_type=TaskType.REPORT_GENERATION,
    content=content,
)

model_info = selector.get_model_info(model_name)
print(f"Usando: {model_info['name']}")
print(f"Provider: {model_info['provider']}")
print(f"Custo: {model_info['cost_tier']}")
```

## Otimização de Custos

### Economia Estimada

Com seleção inteligente vs. usar apenas GPT-4o:

| Cenário | Tarefas/Dia | Custo GPT-4o | Custo Híbrido | Economia |
| ------- | ----------- | ------------ | ------------- | -------- |
| Pequeno | 50          | $15          | $6            | 60%      |
| Médio   | 200         | $60          | $24           | 60%      |
| Grande  | 1000        | $300         | $120          | 60%      |

**Distribuição típica:**

- 40% tarefas simples (MiniMax - grátis)
- 20% tarefas moderadas (MiniMax - grátis)
- 40% tarefas complexas (GPT-4o - pago)

### Melhores Práticas

1. **Use estratégia "auto" em produção**
   - Melhor custo-benefício
   - Qualidade mantida onde necessário

2. **Use "simple" em desenvolvimento**
   - Economia máxima
   - Testes rápidos

3. **Use "complex" para documentos críticos**
   - Máxima qualidade
   - SLA garantido

4. **Configure limites de tokens apropriados**
   - Evite desperdício
   - Mantenha performance

## Monitoramento

### Logs

Cada seleção de modelo é logada:

```json
{
  "event": "model_selected",
  "task": "report_generation",
  "complexity": "complex",
  "model": "gpt-4o",
  "content_length": 5420,
  "provider": "openai",
  "cost_tier": "premium"
}
```

### Métricas

Colete métricas para otimização:

- Distribuição de uso por modelo
- Custo por tipo de tarefa
- Tempo de resposta por modelo
- Taxa de sucesso por modelo

### Dashboard Sugerido

```
┌─────────────────────────────────────┐
│ Uso de Modelos (Últimas 24h)       │
├─────────────────────────────────────┤
│ MiniMax M2.5:  60% (300 requests)   │
│ GPT-4o:        40% (200 requests)   │
├─────────────────────────────────────┤
│ Custo Total: $24.50                 │
│ Economia: $36.50 (60%)              │
└─────────────────────────────────────┘
```

## Troubleshooting

### Problema: MiniMax não funciona

**Sintomas:**

```
WARNING: minimax_key_missing
WARNING: minimax_not_available
```

**Solução:**

1. Verifique se `MINIMAX_API_KEY` está configurada
2. Instale SDK: `pip install langchain-community`
3. Sistema fará fallback automático para OpenAI

### Problema: Custos muito altos

**Sintomas:**

- Fatura OpenAI acima do esperado

**Solução:**

1. Verifique estratégia: deve ser "auto"
2. Revise logs de seleção de modelo
3. Considere ajustar thresholds de complexidade
4. Use "simple" para ambientes de teste

### Problema: Qualidade inconsistente

**Sintomas:**

- Relatórios com qualidade variável

**Solução:**

1. Use estratégia "complex" para tarefas críticas
2. Ajuste mapeamento de complexidade
3. Force modelo específico para casos especiais

## Extensibilidade

### Adicionar Novo Modelo

1. Adicione configuração:

```python
# config.py
new_model: str = "claude-3-opus"
```

2. Implemente criação:

```python
# model_selector.py
def _create_llm(self, model_name: str, ...):
    if model_name.startswith("claude"):
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(...)
```

3. Atualize mapeamento:

```python
TASK_COMPLEXITY_MAP = {
    TaskType.SPECIAL_TASK: TaskComplexity.COMPLEX,
}
```

### Customizar Lógica de Complexidade

```python
def analyze_content_complexity(self, content: str, task_type: TaskType):
    # Sua lógica customizada
    if "urgent" in content.lower():
        return TaskComplexity.COMPLEX

    # Lógica padrão
    return super().analyze_content_complexity(content, task_type)
```

## Referências

- [OpenAI Pricing](https://openai.com/pricing)
- [MiniMax Documentation](https://www.minimaxi.com/docs)
- [LangChain Model Selection](https://python.langchain.com/docs/guides/model_selection)

## Suporte

Para questões sobre seleção de modelos:

- Revise logs estruturados
- Consulte métricas de uso
- Ajuste configuração conforme necessário
- Entre em contato com suporte se problemas persistirem
