"""Markdown → PDF exporter using xhtml2pdf (pure Python, no system libs required)."""
import base64
import os
import re

import markdown
from xhtml2pdf import pisa

CSS_STYLE = """
@page { size: A4; margin: 2cm 2cm 2.5cm 2cm; }
body { font-family: Helvetica, Arial, sans-serif; font-size: 10pt; line-height: 1.6; color: #1a1a1a; }
h1 { font-size: 18pt; color: #1a3a5c; border-bottom: 3px solid #1a3a5c; padding-bottom: 6px; margin-top: 0; }
h2 { font-size: 13pt; color: #1a3a5c; border-bottom: 1px solid #ccc; padding-bottom: 3px; margin-top: 20px; }
h3 { font-size: 11pt; color: #2c5282; margin-top: 14px; }
h4 { font-size: 10pt; color: #2c5282; }
table { width: 100%; border-collapse: collapse; margin: 10px 0; font-size: 8.5pt; }
th { background-color: #1a3a5c; color: white; padding: 5px 7px; text-align: left; font-weight: bold; }
td { padding: 4px 7px; border-bottom: 1px solid #e0e0e0; vertical-align: top; }
tr.even td { background-color: #f5f8fc; }
img { max-width: 100%; height: auto; display: block; margin: 10px auto; }
code { background-color: #f4f4f4; padding: 1px 3px; font-size: 8.5pt; }
pre { background-color: #f4f4f4; padding: 8px; font-size: 8pt; }
blockquote { border-left: 4px solid #1a3a5c; margin: 6px 0; padding: 3px 10px; color: #555; background-color: #f8fafc; }
ul, ol { margin: 5px 0; padding-left: 18px; }
li { margin-bottom: 2px; }
hr { border-top: 1px solid #ddd; margin: 14px 0; }
p { margin: 5px 0; }
"""


def _embed_images(md_text: str) -> str:
    """Embed local images as base64 data URIs."""
    def replace(match):
        alt, path = match.group(1), match.group(2)
        if path.startswith("http") or path.startswith("data:"):
            return match.group(0)
        if os.path.exists(path):
            with open(path, "rb") as f:
                data = base64.b64encode(f.read()).decode()
            ext = os.path.splitext(path)[1].lstrip(".").lower()
            mime = "image/png" if ext == "png" else "image/jpeg"
            return f"![{alt}](data:{mime};base64,{data})"
        return match.group(0)
    return re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", replace, md_text)


def md_to_pdf(md_path: str, pdf_path: str | None = None) -> str:
    if pdf_path is None:
        pdf_path = os.path.splitext(md_path)[0] + ".pdf"
    with open(md_path, "r", encoding="utf-8") as f:
        md_content = f.read()
    return md_string_to_pdf(md_content, pdf_path)


def md_string_to_pdf(md_content: str, pdf_path: str) -> str:
    md_content = _embed_images(md_content)
    html_body = markdown.markdown(
        md_content,
        extensions=["tables", "fenced_code", "nl2br", "toc"],
    )
    html_full = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8"/>
  <title>Relatório</title>
  <style>{CSS_STYLE}</style>
</head>
<body>{html_body}</body>
</html>"""

    os.makedirs(os.path.dirname(pdf_path) or ".", exist_ok=True)
    with open(pdf_path, "wb") as f:
        status = pisa.CreatePDF(html_full, dest=f, encoding="utf-8")

    if status.err:
        raise RuntimeError(f"xhtml2pdf: {status.err} erro(s) ao gerar PDF")

    return pdf_path
