"""Text and Markdown parser."""
import os
from typing import List

from src.core.logging import get_logger
from src.graphs.state import DocumentMetadata, ExtractedSection
from src.parsers.base_parser import BaseParser, ParseResult

logger = get_logger(__name__)


class TextParser(BaseParser):
    """Parser for plain text and markdown files."""
    
    def can_parse(self, file_path: str) -> bool:
        """Check if file is text or markdown."""
        return file_path.lower().endswith((".txt", ".md", ".markdown"))
    
    def parse(self, file_path: str) -> ParseResult:
        """Parse text document."""
        logger.info("parsing_text", file_path=file_path)
        
        warnings: List[str] = []
        sections: List[ExtractedSection] = []
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # For markdown, try to extract sections by headers
            if file_path.lower().endswith((".md", ".markdown")):
                lines = content.split("\n")
                current_section_title = "Introduction"
                current_section_content: List[str] = []
                
                for line in lines:
                    if line.startswith("#"):
                        # Save previous section
                        if current_section_content:
                            sections.append(
                                ExtractedSection(
                                    title=current_section_title,
                                    content="\n".join(current_section_content),
                                    level=line.count("#"),
                                )
                            )
                        # Start new section
                        current_section_title = line.lstrip("#").strip()
                        current_section_content = []
                    else:
                        current_section_content.append(line)
                
                # Save last section
                if current_section_content:
                    sections.append(
                        ExtractedSection(
                            title=current_section_title,
                            content="\n".join(current_section_content),
                            level=1,
                        )
                    )
            else:
                # Plain text - treat as single section
                sections.append(
                    ExtractedSection(
                        title="Content",
                        content=content,
                        level=1,
                    )
                )
            
            normalized_content = self.normalize_text(content)
            
            # Create metadata
            file_size = os.path.getsize(file_path)
            word_count = len(normalized_content.split())
            file_type = "markdown" if file_path.lower().endswith((".md", ".markdown")) else "text"
            
            metadata = DocumentMetadata(
                filename=os.path.basename(file_path),
                file_type=file_type,
                file_size=file_size,
                word_count=word_count,
            )
            
            return ParseResult(
                content=normalized_content,
                metadata=metadata,
                sections=sections,
                tables=[],
                warnings=warnings,
            )
            
        except Exception as e:
            logger.error("text_parsing_failed", error=str(e))
            raise ValueError(f"Failed to parse text file: {str(e)}")
