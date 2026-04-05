"""
Exemplos de uso do sistema de seleção inteligente de modelos.

Este arquivo demonstra como usar o ModelSelector para otimizar custos
escolhendo automaticamente entre modelos gratuitos e premium.
"""

from src.core.model_selector import TaskComplexity, TaskType, get_model_selector


def example_basic_usage():
    """Exemplo básico de uso do seletor de modelo."""
    print("=== Exemplo 1: Uso Básico ===\n")
    
    selector = get_model_selector()
    
    # Obter LLM para parsing (tarefa simples)
    llm = selector.get_llm(task_type=TaskType.PARSING)
    print(f"Parsing: {selector.select_model(TaskType.PARSING)}")
    
    # Obter LLM para geração de relatório (tarefa complexa)
    llm = selector.get_llm(task_type=TaskType.REPORT_GENERATION)
    print(f"Report Generation: {selector.select_model(TaskType.REPORT_GENERATION)}")
    
    # Obter LLM para revisão (tarefa complexa)
    llm = selector.get_llm(task_type=TaskType.REVIEW)
    print(f"Review: {selector.select_model(TaskType.REVIEW)}")
    
    print()


def example_content_based_selection():
    """Exemplo de seleção baseada no conteúdo."""
    print("=== Exemplo 2: Seleção Baseada em Conteúdo ===\n")
    
    selector = get_model_selector()
    
    # Documento curto
    short_doc = "Este é um documento curto. " * 20  # ~100 palavras
    model = selector.select_model(TaskType.ANALYSIS, content=short_doc)
    print(f"Documento curto (análise): {model}")
    
    # Documento médio
    medium_doc = "Este é um documento médio. " * 300  # ~1500 palavras
    model = selector.select_model(TaskType.ANALYSIS, content=medium_doc)
    print(f"Documento médio (análise): {model}")
    
    # Documento longo
    long_doc = "Este é um documento longo. " * 1500  # ~7500 palavras
    model = selector.select_model(TaskType.ANALYSIS, content=long_doc)
    print(f"Documento longo (análise): {model}")
    
    print()


def example_force_complexity():
    """Exemplo de forçar complexidade específica."""
    print("=== Exemplo 3: Forçar Complexidade ===\n")
    
    selector = get_model_selector()
    
    # Forçar modelo simples para tarefa complexa
    model = selector.select_model(
        TaskType.REPORT_GENERATION,
        force_complexity=TaskComplexity.SIMPLE,
    )
    print(f"Report (forçado simples): {model}")
    
    # Forçar modelo complexo para tarefa simples
    model = selector.select_model(
        TaskType.PARSING,
        force_complexity=TaskComplexity.COMPLEX,
    )
    print(f"Parsing (forçado complexo): {model}")
    
    print()


def example_custom_parameters():
    """Exemplo de parâmetros customizados."""
    print("=== Exemplo 4: Parâmetros Customizados ===\n")
    
    selector = get_model_selector()
    
    # LLM com temperatura customizada
    llm = selector.get_llm(
        task_type=TaskType.REPORT_GENERATION,
        temperature=0.7,  # Mais criativo
    )
    print("LLM criado com temperature=0.7")
    
    # LLM com max_tokens customizado
    llm = selector.get_llm(
        task_type=TaskType.REVIEW,
        max_tokens=2000,  # Limite menor
    )
    print("LLM criado com max_tokens=2000")
    
    print()


def example_model_info():
    """Exemplo de obter informações sobre modelos."""
    print("=== Exemplo 5: Informações de Modelos ===\n")
    
    selector = get_model_selector()
    
    models = ["minimax-m2.5", "gpt-4o", "gpt-3.5-turbo"]
    
    for model_name in models:
        info = selector.get_model_info(model_name)
        print(f"{model_name}:")
        print(f"  Provider: {info['provider']}")
        print(f"  Cost Tier: {info['cost_tier']}")
        print(f"  Capabilities: {', '.join(info['capabilities'])}")
        print()


def example_cost_optimization():
    """Exemplo de otimização de custos."""
    print("=== Exemplo 6: Otimização de Custos ===\n")
    
    selector = get_model_selector()
    
    # Simular 100 requisições
    tasks = [
        (TaskType.PARSING, 30),
        (TaskType.SECURITY_SCAN, 20),
        (TaskType.ANALYSIS, 20),
        (TaskType.REPORT_GENERATION, 20),
        (TaskType.REVIEW, 10),
    ]
    
    free_count = 0
    paid_count = 0
    
    for task_type, count in tasks:
        model = selector.select_model(task_type)
        info = selector.get_model_info(model)
        
        if info["cost_tier"] == "free":
            free_count += count
        else:
            paid_count += count
        
        print(f"{task_type.value}: {count}x {model} ({info['cost_tier']})")
    
    print(f"\nTotal: {free_count + paid_count} requisições")
    print(f"Gratuitas: {free_count} ({free_count/(free_count+paid_count)*100:.1f}%)")
    print(f"Pagas: {paid_count} ({paid_count/(free_count+paid_count)*100:.1f}%)")
    print(f"\nEconomia estimada: ~60% vs. usar apenas GPT-4o")
    
    print()


def example_complexity_analysis():
    """Exemplo de análise de complexidade."""
    print("=== Exemplo 7: Análise de Complexidade ===\n")
    
    selector = get_model_selector()
    
    contents = {
        "Curto": "Texto curto. " * 20,
        "Médio": "Texto médio. " * 300,
        "Longo": "Texto longo. " * 1500,
    }
    
    for label, content in contents.items():
        complexity = selector.analyze_content_complexity(
            content,
            TaskType.ANALYSIS,
        )
        word_count = len(content.split())
        print(f"{label} ({word_count} palavras): {complexity.value}")
    
    print()


def example_real_world_workflow():
    """Exemplo de workflow real."""
    print("=== Exemplo 8: Workflow Real ===\n")
    
    selector = get_model_selector()
    
    # Simular processamento de documento
    document_content = "Conteúdo do documento técnico. " * 500
    
    print("Processando documento...")
    print()
    
    # 1. Parsing
    model = selector.select_model(TaskType.PARSING)
    print(f"1. Parsing: {model}")
    
    # 2. Security scan
    model = selector.select_model(TaskType.SECURITY_SCAN)
    print(f"2. Security Scan: {model}")
    
    # 3. Analysis
    model = selector.select_model(TaskType.ANALYSIS, content=document_content)
    print(f"3. Analysis: {model}")
    
    # 4. Report generation
    model = selector.select_model(TaskType.REPORT_GENERATION, content=document_content)
    print(f"4. Report Generation: {model}")
    
    # 5. Review
    report_content = "Relatório gerado. " * 200
    model = selector.select_model(TaskType.REVIEW, content=report_content)
    print(f"5. Review: {model}")
    
    # 6. Export
    model = selector.select_model(TaskType.EXPORT)
    print(f"6. Export: {model}")
    
    print()


if __name__ == "__main__":
    print("=" * 60)
    print("EXEMPLOS DE SELEÇÃO INTELIGENTE DE MODELOS")
    print("=" * 60)
    print()
    
    example_basic_usage()
    example_content_based_selection()
    example_force_complexity()
    example_custom_parameters()
    example_model_info()
    example_cost_optimization()
    example_complexity_analysis()
    example_real_world_workflow()
    
    print("=" * 60)
    print("Para mais informações, veja: docs/MODEL_SELECTION.md")
    print("=" * 60)
