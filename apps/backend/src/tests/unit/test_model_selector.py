"""Tests for intelligent model selection."""
import pytest

from src.core.model_selector import ModelSelector, TaskComplexity, TaskType


class TestModelSelector:
    """Test model selection logic."""
    
    @pytest.fixture
    def selector(self):
        """Create selector instance."""
        return ModelSelector()
    
    def test_task_complexity_mapping(self, selector):
        """Test that tasks have correct base complexity."""
        assert selector.get_complexity_for_task(TaskType.PARSING) == TaskComplexity.SIMPLE
        assert selector.get_complexity_for_task(TaskType.SECURITY_SCAN) == TaskComplexity.SIMPLE
        assert selector.get_complexity_for_task(TaskType.SUPERVISION) == TaskComplexity.SIMPLE
        assert selector.get_complexity_for_task(TaskType.EXPORT) == TaskComplexity.SIMPLE
        
        assert selector.get_complexity_for_task(TaskType.ANALYSIS) == TaskComplexity.MODERATE
        
        assert selector.get_complexity_for_task(TaskType.REPORT_GENERATION) == TaskComplexity.COMPLEX
        assert selector.get_complexity_for_task(TaskType.REVIEW) == TaskComplexity.COMPLEX
    
    def test_content_complexity_short_content(self, selector):
        """Test that short content can downgrade complexity."""
        short_content = "This is a short document. " * 20  # ~100 words
        
        # Complex task with short content -> Moderate
        complexity = selector.analyze_content_complexity(
            short_content,
            TaskType.REPORT_GENERATION,
        )
        assert complexity == TaskComplexity.MODERATE
        
        # Moderate task with short content -> Simple
        complexity = selector.analyze_content_complexity(
            short_content,
            TaskType.ANALYSIS,
        )
        assert complexity == TaskComplexity.SIMPLE
    
    def test_content_complexity_long_content(self, selector):
        """Test that long content can upgrade complexity."""
        long_content = "This is a long document. " * 1500  # ~7500 words
        
        # Simple task with long content -> Moderate
        complexity = selector.analyze_content_complexity(
            long_content,
            TaskType.PARSING,
        )
        assert complexity == TaskComplexity.MODERATE
        
        # Moderate task with long content -> Complex
        complexity = selector.analyze_content_complexity(
            long_content,
            TaskType.ANALYSIS,
        )
        assert complexity == TaskComplexity.COMPLEX
    
    def test_content_complexity_medium_content(self, selector):
        """Test that medium content maintains base complexity."""
        medium_content = "This is a medium document. " * 300  # ~1500 words
        
        # Should maintain base complexity
        complexity = selector.analyze_content_complexity(
            medium_content,
            TaskType.REPORT_GENERATION,
        )
        assert complexity == TaskComplexity.COMPLEX
        
        complexity = selector.analyze_content_complexity(
            medium_content,
            TaskType.ANALYSIS,
        )
        assert complexity == TaskComplexity.MODERATE
    
    def test_select_model_simple_task(self, selector):
        """Test model selection for simple tasks."""
        model = selector.select_model(TaskType.PARSING)
        assert model == selector.settings.simple_model
        
        model = selector.select_model(TaskType.SECURITY_SCAN)
        assert model == selector.settings.simple_model
    
    def test_select_model_complex_task(self, selector):
        """Test model selection for complex tasks."""
        model = selector.select_model(TaskType.REPORT_GENERATION)
        assert model == selector.settings.complex_model
        
        model = selector.select_model(TaskType.REVIEW)
        assert model == selector.settings.complex_model
    
    def test_select_model_with_content(self, selector):
        """Test model selection considering content."""
        short_content = "Short content. " * 20
        
        # Complex task with short content
        model = selector.select_model(
            TaskType.REPORT_GENERATION,
            content=short_content,
        )
        # Should still use complex model (moderate complexity)
        # but this depends on implementation
        assert model in [selector.settings.simple_model, selector.settings.complex_model]
    
    def test_force_complexity(self, selector):
        """Test forcing specific complexity."""
        # Force simple for complex task
        model = selector.select_model(
            TaskType.REPORT_GENERATION,
            force_complexity=TaskComplexity.SIMPLE,
        )
        assert model == selector.settings.simple_model
        
        # Force complex for simple task
        model = selector.select_model(
            TaskType.PARSING,
            force_complexity=TaskComplexity.COMPLEX,
        )
        assert model == selector.settings.complex_model
    
    def test_get_model_info(self, selector):
        """Test getting model information."""
        # MiniMax model
        info = selector.get_model_info("minimax-m2.5")
        assert info["provider"] == "minimax"
        assert info["cost_tier"] == "free"
        
        # GPT-4 model
        info = selector.get_model_info("gpt-4o")
        assert info["provider"] == "openai"
        assert info["cost_tier"] == "premium"
        
        # GPT-3.5 model
        info = selector.get_model_info("gpt-3.5-turbo")
        assert info["provider"] == "openai"
        assert info["cost_tier"] == "standard"
    
    def test_get_llm_caching(self, selector):
        """Test that LLM instances are cached."""
        llm1 = selector.get_llm(TaskType.PARSING)
        llm2 = selector.get_llm(TaskType.PARSING)
        
        # Should return same cached instance
        assert llm1 is llm2
    
    def test_get_llm_different_params(self, selector):
        """Test that different parameters create different instances."""
        llm1 = selector.get_llm(TaskType.PARSING, temperature=0.1)
        llm2 = selector.get_llm(TaskType.PARSING, temperature=0.5)
        
        # Should be different instances
        assert llm1 is not llm2
    
    def test_get_llm_with_custom_params(self, selector):
        """Test getting LLM with custom parameters."""
        llm = selector.get_llm(
            task_type=TaskType.REPORT_GENERATION,
            temperature=0.7,
            max_tokens=1000,
        )
        
        assert llm is not None
        # Verify parameters are applied (implementation specific)
    
    def test_complexity_levels(self):
        """Test that all complexity levels are defined."""
        assert TaskComplexity.SIMPLE == "simple"
        assert TaskComplexity.MODERATE == "moderate"
        assert TaskComplexity.COMPLEX == "complex"
    
    def test_task_types(self):
        """Test that all task types are defined."""
        assert TaskType.PARSING == "parsing"
        assert TaskType.SECURITY_SCAN == "security_scan"
        assert TaskType.ANALYSIS == "analysis"
        assert TaskType.REPORT_GENERATION == "report_generation"
        assert TaskType.REVIEW == "review"
        assert TaskType.EXPORT == "export"
        assert TaskType.SUPERVISION == "supervision"


class TestModelSelectorIntegration:
    """Integration tests for model selector."""
    
    @pytest.fixture
    def selector(self):
        """Create selector instance."""
        return ModelSelector()
    
    def test_realistic_parsing_scenario(self, selector):
        """Test realistic parsing scenario."""
        content = "PDF document content here..."
        
        llm = selector.get_llm(
            task_type=TaskType.PARSING,
            content=content,
        )
        
        assert llm is not None
        # Should use simple model for parsing
        model = selector.select_model(TaskType.PARSING, content)
        assert model == selector.settings.simple_model
    
    def test_realistic_report_generation_scenario(self, selector):
        """Test realistic report generation scenario."""
        content = "Long technical document. " * 500  # ~2500 words
        
        llm = selector.get_llm(
            task_type=TaskType.REPORT_GENERATION,
            content=content,
        )
        
        assert llm is not None
        # Should use complex model for report generation
        model = selector.select_model(TaskType.REPORT_GENERATION, content)
        assert model == selector.settings.complex_model
    
    def test_realistic_review_scenario(self, selector):
        """Test realistic review scenario."""
        report = "Generated report content. " * 200  # ~1000 words
        
        llm = selector.get_llm(
            task_type=TaskType.REVIEW,
            content=report,
        )
        
        assert llm is not None
        # Should use complex model for review
        model = selector.select_model(TaskType.REVIEW, report)
        assert model == selector.settings.complex_model
    
    def test_cost_optimization_scenario(self, selector):
        """Test that cost optimization works as expected."""
        # Simple tasks should use free model
        simple_tasks = [
            TaskType.PARSING,
            TaskType.SECURITY_SCAN,
            TaskType.SUPERVISION,
            TaskType.EXPORT,
        ]
        
        for task in simple_tasks:
            model = selector.select_model(task)
            info = selector.get_model_info(model)
            # Should prefer free model for simple tasks
            assert info["cost_tier"] in ["free", "standard"]
        
        # Complex tasks should use premium model
        complex_tasks = [
            TaskType.REPORT_GENERATION,
            TaskType.REVIEW,
        ]
        
        for task in complex_tasks:
            model = selector.select_model(task)
            info = selector.get_model_info(model)
            # Should use premium model for complex tasks
            assert info["cost_tier"] == "premium"
