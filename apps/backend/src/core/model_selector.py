"""Intelligent model selection based on task complexity."""
from enum import Enum
from typing import Optional

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

from src.core.config import get_settings
from src.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class TaskComplexity(str, Enum):
    """Task complexity levels."""
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"


class TaskType(str, Enum):
    """Types of tasks in the system."""
    PARSING = "parsing"
    SECURITY_SCAN = "security_scan"
    ANALYSIS = "analysis"
    REPORT_GENERATION = "report_generation"
    REVIEW = "review"
    EXPORT = "export"
    SUPERVISION = "supervision"


class ModelSelector:
    """Selects appropriate LLM based on task complexity."""
    
    # Task complexity mapping
    TASK_COMPLEXITY_MAP = {
        TaskType.PARSING: TaskComplexity.SIMPLE,
        TaskType.SECURITY_SCAN: TaskComplexity.SIMPLE,
        TaskType.ANALYSIS: TaskComplexity.MODERATE,
        TaskType.SUPERVISION: TaskComplexity.SIMPLE,
        TaskType.REPORT_GENERATION: TaskComplexity.COMPLEX,
        TaskType.REVIEW: TaskComplexity.COMPLEX,
        TaskType.EXPORT: TaskComplexity.SIMPLE,
    }
    
    def __init__(self) -> None:
        """Initialize model selector."""
        self.settings = settings
        self._model_cache: dict[str, BaseChatModel] = {}
    
    def get_complexity_for_task(self, task_type: TaskType) -> TaskComplexity:
        """Determine complexity level for a task type."""
        return self.TASK_COMPLEXITY_MAP.get(task_type, TaskComplexity.MODERATE)
    
    def analyze_content_complexity(
        self,
        content: str,
        task_type: TaskType,
    ) -> TaskComplexity:
        """
        Analyze content to determine complexity.
        
        Factors considered:
        - Content length
        - Task type
        - Structural complexity
        """
        base_complexity = self.get_complexity_for_task(task_type)
        
        # Content length analysis
        word_count = len(content.split())
        
        # Adjust complexity based on content length
        if word_count < 500:
            # Short content - can downgrade complexity
            if base_complexity == TaskComplexity.COMPLEX:
                return TaskComplexity.MODERATE
            elif base_complexity == TaskComplexity.MODERATE:
                return TaskComplexity.SIMPLE
        elif word_count > 5000:
            # Long content - may need upgrade
            if base_complexity == TaskComplexity.SIMPLE:
                return TaskComplexity.MODERATE
            elif base_complexity == TaskComplexity.MODERATE:
                return TaskComplexity.COMPLEX
        
        return base_complexity
    
    def select_model(
        self,
        task_type: TaskType,
        content: Optional[str] = None,
        force_complexity: Optional[TaskComplexity] = None,
    ) -> str:
        """
        Select appropriate model for the task.
        
        Args:
            task_type: Type of task to perform
            content: Optional content to analyze for complexity
            force_complexity: Force a specific complexity level
            
        Returns:
            Model name to use
        """
        # Check if strategy is set to specific model
        if self.settings.model_selection_strategy not in ["auto", "simple", "complex"]:
            model_name = self.settings.model_selection_strategy
            logger.info("using_specific_model", model=model_name, task=task_type)
            return model_name
        
        # Determine complexity
        if force_complexity:
            complexity = force_complexity
        elif content:
            complexity = self.analyze_content_complexity(content, task_type)
        else:
            complexity = self.get_complexity_for_task(task_type)
        
        # Override with strategy if set
        if self.settings.model_selection_strategy == "simple":
            complexity = TaskComplexity.SIMPLE
        elif self.settings.model_selection_strategy == "complex":
            complexity = TaskComplexity.COMPLEX
        
        # Select model based on complexity
        if complexity == TaskComplexity.SIMPLE:
            model_name = self.settings.simple_model
        elif complexity == TaskComplexity.COMPLEX:
            model_name = self.settings.complex_model
        else:  # MODERATE
            # Use simple model for moderate tasks to save costs
            # Can be adjusted based on requirements
            model_name = self.settings.simple_model
        
        logger.info(
            "model_selected",
            task=task_type,
            complexity=complexity,
            model=model_name,
            content_length=len(content) if content else 0,
        )
        
        return model_name
    
    def get_llm(
        self,
        task_type: TaskType,
        content: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        force_complexity: Optional[TaskComplexity] = None,
    ) -> BaseChatModel:
        """
        Get configured LLM instance for the task.
        
        Args:
            task_type: Type of task
            content: Optional content for complexity analysis
            temperature: Override temperature
            max_tokens: Override max tokens
            force_complexity: Force specific complexity
            
        Returns:
            Configured LLM instance
        """
        model_name = self.select_model(task_type, content, force_complexity)
        
        # Determine parameters based on complexity
        if force_complexity:
            complexity = force_complexity
        elif content:
            complexity = self.analyze_content_complexity(content, task_type)
        else:
            complexity = self.get_complexity_for_task(task_type)
        
        # Set default parameters based on complexity
        if temperature is None:
            temperature = self.settings.default_temperature
        
        if max_tokens is None:
            if complexity == TaskComplexity.SIMPLE:
                max_tokens = self.settings.simple_task_max_tokens
            else:
                max_tokens = self.settings.complex_task_max_tokens
        
        # Create cache key
        cache_key = f"{model_name}_{temperature}_{max_tokens}"
        
        # Return cached instance if available
        if cache_key in self._model_cache:
            return self._model_cache[cache_key]
        
        # Create new LLM instance
        llm = self._create_llm(model_name, temperature, max_tokens)
        
        # Cache it
        self._model_cache[cache_key] = llm
        
        return llm
    
    def _create_llm(
        self,
        model_name: str,
        temperature: float,
        max_tokens: int,
    ) -> BaseChatModel:
        """Create LLM instance based on model name."""
        
        # MiniMax models
        if model_name.startswith("minimax"):
            if not self.settings.minimax_api_key:
                logger.warning(
                    "minimax_key_missing",
                    message="MiniMax API key not configured, falling back to OpenAI",
                )
                model_name = self.settings.complex_model
            else:
                # MiniMax integration
                # Note: You'll need to add minimax SDK to requirements
                try:
                    from langchain_community.chat_models import ChatMiniMax
                    
                    return ChatMiniMax(
                        model=model_name,
                        minimax_api_key=self.settings.minimax_api_key,
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )
                except ImportError:
                    logger.warning(
                        "minimax_not_available",
                        message="MiniMax SDK not installed, falling back to OpenAI",
                    )
                    model_name = self.settings.complex_model
        
        # OpenAI models (default)
        return ChatOpenAI(
            model=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=self.settings.openai_api_key,
        )
    
    def get_model_info(self, model_name: str) -> dict:
        """Get information about a model."""
        info = {
            "name": model_name,
            "provider": "unknown",
            "cost_tier": "unknown",
            "capabilities": [],
        }
        
        if model_name.startswith("minimax"):
            info["provider"] = "minimax"
            info["cost_tier"] = "free"
            info["capabilities"] = ["text_generation", "chat"]
        elif model_name.startswith("gpt-4"):
            info["provider"] = "openai"
            info["cost_tier"] = "premium"
            info["capabilities"] = ["text_generation", "chat", "function_calling"]
        elif model_name.startswith("gpt-3.5"):
            info["provider"] = "openai"
            info["cost_tier"] = "standard"
            info["capabilities"] = ["text_generation", "chat", "function_calling"]
        
        return info


# Global instance
_model_selector: Optional[ModelSelector] = None


def get_model_selector() -> ModelSelector:
    """Get global model selector instance."""
    global _model_selector
    if _model_selector is None:
        _model_selector = ModelSelector()
    return _model_selector
