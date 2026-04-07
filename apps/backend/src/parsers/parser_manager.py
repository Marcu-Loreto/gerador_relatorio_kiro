"""Parser manager to route files to appropriate parsers."""
from typing import List

from src.core.logging import get_logger
from src.parsers.base_parser import BaseParser, ParseResult
from src.parsers.csv_parser import CSVParser
from src.parsers.docx_parser import DOCXParser
from src.parsers.pdf_parser import PDFParser
from src.parsers.pptx_parser import PPTXParser
from src.parsers.text_parser import TextParser

logger = get_logger(__name__)


class ParserManager:
    """Manages document parsers."""
    
    def __init__(self) -> None:
        """Initialize parser manager with available parsers."""
        self.parsers: List[BaseParser] = [
            PDFParser(),
            DOCXParser(),
            PPTXParser(),
            CSVParser(),
            TextParser(),
        ]
    
    def parse(self, file_path: str) -> ParseResult:
        """Parse a document using the appropriate parser."""
        logger.info("selecting_parser", file_path=file_path)
        
        for parser in self.parsers:
            if parser.can_parse(file_path):
                logger.info("parser_selected", parser=parser.__class__.__name__)
                return parser.parse(file_path)
        
        raise ValueError(f"No parser available for file: {file_path}")
