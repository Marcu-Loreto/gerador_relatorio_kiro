"""Persist report markdown files to disk under reports/."""
import os
import re
from datetime import datetime

REPORTS_DIR = os.environ.get("REPORTS_DIR", "reports")


def _safe_name(name: str) -> str:
    """Sanitize string for use in filename."""
    name = re.sub(r"[^\w\-.]", "_", name)
    return name[:60].strip("_")


def save_report_file(
    report_id: str,
    document_name: str,
    report_type: str,
    markdown: str,
) -> str:
    """
    Save markdown to reports/<YYYY-MM>/<doc_name>_<type>_<id8>.md
    Returns the relative file path.
    """
    month_dir = os.path.join(REPORTS_DIR, datetime.utcnow().strftime("%Y-%m"))
    os.makedirs(month_dir, exist_ok=True)

    doc_slug = _safe_name(os.path.splitext(document_name)[0])
    type_slug = _safe_name(report_type)
    filename = f"{doc_slug}__{type_slug}__{report_id[:8]}.md"
    filepath = os.path.join(month_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(markdown)

    return filepath


def read_report_file(md_path: str) -> str:
    """Read markdown content from disk."""
    if not md_path or not os.path.exists(md_path):
        return ""
    with open(md_path, "r", encoding="utf-8") as f:
        return f.read()


def delete_report_file(md_path: str) -> None:
    """Remove file from disk if it exists."""
    if md_path and os.path.exists(md_path):
        os.remove(md_path)
