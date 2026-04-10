"""PDF document parser."""
import os
from typing import List

import fitz  # PyMuPDF
import pdfplumber

from src.core.logging import get_logger
from src.graphs.state import DocumentMetadata, ExtractedSection, ExtractedTable
from src.parsers.base_parser import BaseParser, ParseResult

logger = get_logger(__name__)


class PDFParser(BaseParser):
    """Parser for PDF documents."""
    
    def can_parse(self, file_path: str) -> bool:
        """Check if file is a PDF."""
        return file_path.lower().endswith(".pdf")
    
    def parse(self, file_path: str) -> ParseResult:
        """Parse PDF document."""
        logger.info("parsing_pdf", file_path=file_path)
        
        warnings: List[str] = []
        content_parts: List[str] = []
        sections: List[ExtractedSection] = []
        tables: List[ExtractedTable] = []
        
        # Extract text with PyMuPDF (fast)
        try:
            doc = fitz.open(file_path)
            page_count = len(doc)
            
            for page_num, page in enumerate(doc, start=1):
                text = page.get_text()
                if text.strip():
                    content_parts.append(text)
                    sections.append(
                        ExtractedSection(
                            title=f"Page {page_num}",
                            content=text,
                            level=1,
                            page=page_num,
                        )
                    )
            
            doc.close()
        except Exception as e:
            logger.error("pymupdf_extraction_failed", error=str(e))
            warnings.append(f"PyMuPDF extraction failed: {str(e)}")
            page_count = 0
        
        # Extract tables with pdfplumber only for small PDFs (< 30 pages)
        # pdfplumber is slow — skip for large documents
        if page_count <= 30:
            try:
                with pdfplumber.open(file_path) as pdf:
                    for page_num, page in enumerate(pdf.pages, start=1):
                        page_tables = page.extract_tables()
                        for table_data in page_tables:
                            if table_data and len(table_data) > 1:
                                headers = table_data[0]
                                rows = table_data[1:]
                                tables.append(
                                    ExtractedTable(
                                        headers=headers,
                                        rows=rows,
                                        page=page_num,
                                    )
                                )
            except Exception as e:
                logger.warning("pdfplumber_table_extraction_failed", error=str(e))
                warnings.append(f"Table extraction failed: {str(e)}")
        else:
            warnings.append(f"Table extraction skipped for large PDF ({page_count} pages)")
        
        # Combine content
        full_content = "\n\n".join(content_parts)
        normalized_content = self.normalize_text(full_content)
        
        # Create metadata
        file_size = os.path.getsize(file_path)
        word_count = len(normalized_content.split())
        
        metadata = DocumentMetadata(
            filename=os.path.basename(file_path),
            file_type="pdf",
            file_size=file_size,
            page_count=page_count,
            word_count=word_count,
        )
        
        return ParseResult(
            content=normalized_content,
            metadata=metadata,
            sections=sections,
            tables=tables,
            warnings=warnings,
        )
