"""Markdown → PDF exporter using WeasyPrint."""
import base64, os, re
import markdown
from weasyprint import CSS, HTML
from weasyprint.text.fonts import FontConfiguration

CSS_STYLE = """
@page { size: A4; margin: 2cm 2cm 2.5cm 2cm;
  @bottom-center { content: "Página " counter(page) " de " counter(pages); font-size: 9pt; color: #666; } }
body { font-family: "DejaVu Sans", Arial, sans-serif; font-size: 10.5pt; line-height: 1.6; color: #1a1a1a; }
h1 { font-size: 18pt; color: #1a3a5c; border-bottom: 3px solid #1a3a5c; padding-bottom: 8px; margin-top: 0; page-break-after: avoid; }
h2 { font-size: 13pt; color: #1a3a5c; border-bottom: 1px solid #ccc; padding-bottom: 4px; margin-top: 24px; page-break-after: avoid; }
h3 { font-size: 11pt; color: #2c5282; margin-top: 16px; page-break-after: avoid; }
h4 { font-size: 10.5pt; color: #2c5282; page-break-after: avoid; }
table { width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 9pt; page-break-inside: avoid; }
th { background-color: #1a3a5c; color: white; padding: 6px 8px; text-align: left; font-weight: bold; }
td { padding: 5px 8px; border-bottom: 1px solid #e0e0e0; vertical-align: top; }
tr:nth-child(even) td { background-color: #f5f8fc; }
img { max-width: 100%; height: auto; display: block; margin: 12px auto; page-break-inside: avoid; }
code { background-color: #f4f4f4; padding: 1px 4px; border-radius: 3px; font-size: 9pt; }
pre { background-color: #f4f4f4; padding: 10px; border-radius: 4px; font-size: 8.5pt; page-break-inside: avoid; }
blockquote { border-left: 4px solid #1a3a5c; margin: 8px 0; padding: 4px 12px; color: #555; background-color: #f8fafc; }
ul, ol { margin: 6px 0; padding-left: 20px; }
li { margin-bottom: 3px; }
hr { border: none; border-top: 1px solid #ddd; margin: 16px 0; }
p { margin: 6px 0; text-align: justify; }
"""

def _embed_images(md_text: str) -> str:
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
    html_body = markdown.markdown(md_content, extensions=["tables", "fenced_code", "nl2br", "toc"])
    html_full = f"""<!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8"><title>Relatório</title></head><body>{html_body}</body></html>"""
    font_config = FontConfiguration()
    css = CSS(string=CSS_STYLE, font_config=font_config)
    HTML(string=html_full, base_url=".").write_pdf(pdf_path, stylesheets=[css], font_config=font_config)
    return pdf_path
