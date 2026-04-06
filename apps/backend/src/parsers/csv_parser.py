"""CSV and Excel document parser."""
import os
from typing import List

import pandas as pd

from src.core.logging import get_logger
from src.graphs.state import DocumentMetadata, ExtractedSection, ExtractedTable
from src.parsers.base_parser import BaseParser, ParseResult

logger = get_logger(__name__)


class CSVParser(BaseParser):
    """Parser for CSV and Excel files."""

    def can_parse(self, file_path: str) -> bool:
        return file_path.lower().endswith((".csv", ".xlsx", ".xls"))

    def parse(self, file_path: str) -> ParseResult:
        logger.info("parsing_csv", file_path=file_path)
        warnings: List[str] = []

        try:
            ext = os.path.splitext(file_path)[1].lower()
            if ext == ".csv":
                df = pd.read_csv(file_path, encoding="utf-8", on_bad_lines="skip")
            else:
                df = pd.read_excel(file_path)
        except Exception as e:
            raise ValueError(f"Failed to parse CSV/Excel: {e}")

        # Build readable text content
        rows_text: List[str] = []
        rows_text.append(f"Colunas: {', '.join(str(c) for c in df.columns)}")
        rows_text.append(f"Total de registros: {len(df)}")
        rows_text.append("")

        # Sample rows for content (first 100)
        for _, row in df.head(100).iterrows():
            row_str = " | ".join(f"{col}: {val}" for col, val in row.items() if pd.notna(val))
            rows_text.append(row_str)

        if len(df) > 100:
            rows_text.append(f"... e mais {len(df) - 100} registros.")

        content = "\n".join(rows_text)

        # Build extracted table
        headers = [str(c) for c in df.columns]
        table_rows = [
            [str(v) if pd.notna(v) else "" for v in row]
            for _, row in df.head(200).iterrows()
        ]
        tables = [ExtractedTable(headers=headers, rows=table_rows)]

        # Sections by column groupings
        sections = [
            ExtractedSection(
                title="Visão Geral do Dataset",
                content=f"Colunas: {', '.join(headers)}\nRegistros: {len(df)}",
                level=1,
            )
        ]

        # Add value counts for categorical columns
        for col in df.select_dtypes(include="object").columns[:5]:
            counts = df[col].value_counts().head(10)
            section_content = f"Distribuição de '{col}':\n"
            for val, cnt in counts.items():
                section_content += f"  - {val}: {cnt}\n"
            sections.append(ExtractedSection(title=f"Coluna: {col}", content=section_content, level=2))

        metadata = DocumentMetadata(
            filename=os.path.basename(file_path),
            file_type=ext.lstrip("."),
            file_size=os.path.getsize(file_path),
            word_count=len(content.split()),
        )

        return ParseResult(
            content=content,
            metadata=metadata,
            sections=sections,
            tables=tables,
            warnings=warnings,
        )
