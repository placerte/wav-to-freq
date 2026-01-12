# src/wav_to_freq/reporting/writers/pdf.py
"""
PDF export for wav-to-freq reports.

Option 2A strategy:
1) If `pandoc` is available, try using it (best fidelity).
2) If pandoc is missing OR pandoc fails (e.g., missing LaTeX engine), fall back to:
   Markdown -> HTML -> PDF using WeasyPrint (no external executables).

Notes:
- WeasyPrint still depends on native libs, but they are bundled with wheels/packagers
  (no separate user install of pandoc/latex needed).
- Relative image paths are resolved against `root_dir` (typically your out_dir).
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence, Union


@dataclass(frozen=True)
class PdfExportResult:
    pdf_path: Path
    engine: str  # "pandoc" or "weasyprint"


def md_to_pdf(
    md_paths: Union[Path, Sequence[Path]],
    pdf_path: Optional[Path] = None,
    *,
    root_dir: Optional[Path] = None,
    title: Optional[str] = None,
    prefer_pandoc: bool = True,
) -> PdfExportResult:
    """
    Convert one or more Markdown files to a single PDF.

    Args:
        md_paths: A single .md file or a sequence of .md files (concatenated in order).
        pdf_path: Output PDF path. Defaults to <first_md>.with_suffix(".pdf").
        root_dir: Base directory used to resolve relative images/links.
                  Defaults to parent of the first markdown file.
        title: Optional title injected at top (only for WeasyPrint fallback).
               Pandoc path: use YAML front-matter in your md if you want full control.
        prefer_pandoc: If True, try pandoc first when available.

    Returns:
        PdfExportResult with output path and engine used.

    Raises:
        FileNotFoundError: if any md file is missing.
        RuntimeError: if neither pandoc nor weasyprint pipeline can run.
        ValueError: if md_paths is empty.
    """
    md_list = _normalize_md_paths(md_paths)
    first_md = md_list[0]

    out_pdf = Path(pdf_path) if pdf_path is not None else first_md.with_suffix(".pdf")
    out_pdf.parent.mkdir(parents=True, exist_ok=True)

    base_dir = Path(root_dir) if root_dir is not None else first_md.parent

    # 1) Try pandoc if requested and available.
    pandoc_ok = prefer_pandoc and _pandoc_available()
    if pandoc_ok:
        #header_tex_path = (Path(__file__).resolve().parent / "../latex/header.tex").resolve()
        # inside md_to_pdf(), right before _render_with_pandoc(...)
        header_tex_path = out_pdf.parent / "_wav_to_freq_header.tex"
        header_tex_path.write_text(
            "\\usepackage{float}\n"
            "\\floatplacement{figure}{H}\n"
            "\\floatplacement{table}{H}\n",
            encoding="utf-8",
        )
        try:
            _render_with_pandoc(md_list, out_pdf, root_dir=base_dir, header_tex_path=header_tex_path)
            return PdfExportResult(pdf_path=out_pdf, engine="pandoc")
        except subprocess.CalledProcessError as e:
            print("Pandoc failed:\n", e.stderr)
            raise
    # 2) Fallback to WeasyPrint (Markdown -> HTML -> PDF).
    _render_with_weasyprint(md_list, out_pdf, root_dir=base_dir, title=title)
    return PdfExportResult(pdf_path=out_pdf, engine="weasyprint")


# -------------------------
# Pandoc renderer
# -------------------------

def _pandoc_available() -> bool:
    return shutil.which("pandoc") is not None


def _render_with_pandoc(md_list: Sequence[Path], pdf_path: Path, *, root_dir: Path,header_tex_path: Path) -> None:
    """
    Uses pandoc to render PDF.
    This typically needs a PDF engine (LaTeX, etc.) installed on the system.
    """
    # pandoc resolves images relative to current working dir and/or resource path.
    # We'll set cwd=root_dir and provide --resource-path.
    cmd = [
        "pandoc",
        "--from=gfm",
        *[str(p) for p in md_list],
        "-o",
        str(pdf_path),
        "--resource-path",
        str(root_dir),
        "--include-in-header",
        str(header_tex_path),
    ]

    subprocess.run(
        cmd,
        cwd=str(root_dir),
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


# -------------------------
# WeasyPrint renderer
# -------------------------

def _render_with_weasyprint(
    md_list: Sequence[Path],
    pdf_path: Path,
    *,
    root_dir: Path,
    title: Optional[str],
) -> None:
    """
    Renders Markdown via a Python Markdown library to HTML, then HTML to PDF with WeasyPrint.
    No external executables required.
    """
    try:
        from weasyprint import HTML  # type: ignore
    except Exception as e:  # pragma: no cover
        raise RuntimeError(
            "WeasyPrint is not installed, and pandoc was unavailable or failed. "
            "Add 'weasyprint' to your dependencies to enable PDF export without pandoc."
        ) from e

    md_text = "\n\n".join(p.read_text(encoding="utf-8", errors="replace") for p in md_list)
    html_body = _markdown_to_html(md_text)

    doc_title = title or (md_list[0].stem if md_list else "Report")

    html_full = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>{_html_escape(doc_title)}</title>
<style>
  @page {{
    size: letter;
    margin: 0.75in;
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
    # base_url is crucial: it makes relative image paths resolve against root_dir
    HTML(string=html_full, base_url=str(root_dir)).write_pdf(str(pdf_path))


def _markdown_to_html(md_text: str) -> str:
    """
    Convert markdown to HTML using whichever lib is available:
    - markdown-it-py (preferred)
    - markdown (python-markdown)
    """
    # Try markdown-it-py first (usually better CommonMark-ish behavior)
    try:
        from markdown_it import MarkdownIt  # type: ignore

        md = MarkdownIt("commonmark", {"html": False})
        return md.render(md_text)
    except Exception:
        pass

    # Fallback to python-markdown
    try:
        import markdown as mdlib  # type: ignore

        return mdlib.markdown(
            md_text,
            extensions=[
                "tables",
                "fenced_code",
                "sane_lists",
                "toc",  # harmless even if you don't use it
            ],
            output_format="html5",
        )
    except Exception as e:  # pragma: no cover
        raise RuntimeError(
            "No Markdown->HTML library is installed. Install either "
            "'markdown-it-py' or 'markdown' to use the WeasyPrint fallback."
        ) from e


# -------------------------
# Helpers
# -------------------------

def _normalize_md_paths(md_paths: Union[Path, Sequence[Path]]) -> list[Path]:
    if isinstance(md_paths, (str, Path)):
        md_list = [Path(md_paths)]
    else:
        md_list = [Path(p) for p in md_paths]

    if not md_list:
        raise ValueError("md_paths is empty")

    for p in md_list:
        if not p.exists():
            raise FileNotFoundError(p)

    return md_list


def _html_escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )

