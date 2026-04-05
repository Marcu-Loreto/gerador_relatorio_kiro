"""Base parser interface."""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from src.graphs.state import DocumentMetadata, ExtractedSection, ExtractedTable


class ParseResult:
    """Result of document parsing."""
    
    def __init__(
        self,
        content: str,
        metadata: DocumentMetadata,
        sections: Optional[List[ExtractedSection]] = None,
        tables: Optional[List[ExtractedTable]] = None,
        warnings: Optional[List[str]] = None,
    ):
        self.content = content
        self.metadata = metadata
        self.sections = sections or []
        self.tables = tables or []
        self.warnings = warnings or []


class BaseParser(ABC):
    """Base class for document parsers."""
    
    @abstractmethod
    def can_parse(self, file_path: str) -> bool:
        """Check if this parser can handle the file."""
        pass
    
    @abstractmethod
    def parse(self, file_path: str) -> ParseResult:
        """Parse the document and extract content."""
        pass
    
    def normalize_text(self, text: str) -> str:
        """Normalize extracted text."""
        # Remove excessive whitespace
        text = " ".join(text.split())
        # Remove null bytes
        text = text.replace("\x00", "")
        return text.strip()
