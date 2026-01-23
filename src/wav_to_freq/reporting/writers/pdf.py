"""PDF export for wav-to-freq reports."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from wav_to_freq.reporting.doc import ReportDoc
from wav_to_freq.reporting.renderers.latex import render_latex
from wav_to_freq.reporting.renderers.markdown import render_markdown


@dataclass(frozen=True)
class PdfExportResult:
    pdf_path: Path
    engine: str  # "pdflatex" or "weasyprint"


def report_to_pdf(
    doc: ReportDoc,
    *,
    pdf_path: Path,
    root_dir: Path,
    title: Optional[str] = None,
    prefer_latex: bool = True,
) -> PdfExportResult:
    out_pdf = Path(pdf_path)
    out_pdf.parent.mkdir(parents=True, exist_ok=True)

    if prefer_latex and _pdflatex_available():
        tex_text = render_latex(doc, title=title, root_dir=root_dir)
        tex_path = out_pdf.with_suffix(".tex")
        tex_path.write_text(tex_text, encoding="utf-8")
        _render_with_pdflatex(tex_path, out_pdf, root_dir=root_dir)
        return PdfExportResult(pdf_path=out_pdf, engine="pdflatex")

    md_text = render_markdown(doc)
    _render_with_weasyprint_text(md_text, out_pdf, root_dir=root_dir, title=title)
    return PdfExportResult(pdf_path=out_pdf, engine="weasyprint")


def _pdflatex_available() -> bool:
    return shutil.which("pdflatex") is not None


def _render_with_pdflatex(tex_path: Path, pdf_path: Path, *, root_dir: Path) -> None:
    cmd = [
        "pdflatex",
        "-interaction=nonstopmode",
        "-halt-on-error",
        "-output-directory",
        str(pdf_path.parent),
        str(tex_path),
    ]
    subprocess.run(
        cmd,
        cwd=str(root_dir),
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def _render_with_weasyprint_text(
    md_text: str,
    pdf_path: Path,
    *,
    root_dir: Path,
    title: Optional[str],
) -> None:
    try:
        from weasyprint import HTML  # type: ignore
    except Exception as e:  # pragma: no cover
        raise RuntimeError(
            "WeasyPrint is not installed and pdflatex is unavailable. "
            "Install 'weasyprint' or a LaTeX engine to enable PDF export."
        ) from e

    html_body = _markdown_to_html(md_text)
    doc_title = title or "Report"

    html_full = f"""<!doctype html>
<html>
<head>
<meta charset=\"utf-8\">
<title>{_html_escape(doc_title)}</title>
<style>
  @page {{
    size: letter;
    margin: 0.5in;
  }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
    font-size: 11pt;
    line-height: 1.35;
  }}
  h1, h2, h3 {{
    margin: 0.8em 0 0.3em 0;
  }}
  p {{
    margin: 0.35em 0;
  }}
  img {{
    max-width: 100%;
    height: auto;
  }}
  table {{
    border-collapse: collapse;
    width: 100%;
    margin: 0.6em 0;
  }}
  th, td {{
    border: 1px solid #999;
    padding: 4px 6px;
    vertical-align: top;
  }}
  code, pre {{
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace;
    font-size: 10pt;
  }}
  pre {{
    white-space: pre-wrap;
  }}
</style>
</head>
<body>
{f"<h1>{_html_escape(doc_title)}</h1>" if title else ""}
{html_body}
</body>
</html>
"""
    HTML(string=html_full, base_url=str(root_dir)).write_pdf(str(pdf_path))


def _markdown_to_html(md_text: str) -> str:
    try:
        from markdown_it import MarkdownIt  # type: ignore

        md = MarkdownIt("commonmark", {"html": False})
        return md.render(md_text)
    except Exception:
        pass

    try:
        import markdown as mdlib  # type: ignore

        return mdlib.markdown(
            md_text,
            extensions=["tables", "fenced_code", "sane_lists", "toc"],
            output_format="html",
        )
    except Exception as e:  # pragma: no cover
        raise RuntimeError(
            "No Markdown->HTML library is installed. Install either "
            "'markdown-it-py' or 'markdown' to use the WeasyPrint fallback."
        ) from e


def _html_escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )
