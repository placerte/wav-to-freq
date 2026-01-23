from __future__ import annotations

from pathlib import Path

from wav_to_freq.reporting.doc import (
    BulletList,
    CodeBlock,
    DocNode,
    Heading,
    Image,
    Paragraph,
    ReportDoc,
    Table,
)


def render_latex(
    doc: ReportDoc,
    *,
    title: str | None = None,
    root_dir: Path | None = None,
) -> str:
    body: list[str] = []
    for node in doc.nodes:
        body.extend(_render_node(node))

    preamble = _latex_preamble(title=title, root_dir=root_dir)
    return "\n".join([preamble, "\\begin{document}", *body, "\\end{document}"])


def _render_node(node: DocNode) -> list[str]:
    if isinstance(node, Heading):
        return [_render_heading(node)]
    if isinstance(node, Paragraph):
        return [_latex_escape(node.text), ""]
    if isinstance(node, BulletList):
        lines = ["\\begin{itemize}"]
        lines.extend([f"  \\item {_latex_escape(item)}" for item in node.items])
        lines.append("\\end{itemize}")
        lines.append("")
        return lines
    if isinstance(node, CodeBlock):
        return ["\\begin{verbatim}", node.code.rstrip(), "\\end{verbatim}", ""]
    if isinstance(node, Image):
        path = _latex_escape(node.path)
        return [
            "\\begin{figure}[H]",
            "  \\centering",
            f"  \\includegraphics[width=\\linewidth]{{{path}}}",
            f"  \\caption*{{{_latex_escape(node.alt)}}}" if node.alt else "",
            "\\end{figure}",
            "",
        ]
    if isinstance(node, Table):
        return _render_table(node)
    return []


def _render_heading(node: Heading) -> str:
    text = _latex_escape(node.text)
    if node.level == 1:
        return f"\\section*{{{text}}}"
    if node.level == 2:
        return f"\\subsection*{{{text}}}"
    return f"\\subsubsection*{{{text}}}"


def _render_table(table: Table) -> list[str]:
    headers = table.headers
    cols = "|" + "|".join(["l"] * len(headers)) + "|"
    lines = ["\\begin{longtable}" + "{" + cols + "}", "\\hline"]

    if table.header_groups:
        lines.append(_render_group_header(table.header_groups, len(headers)))
        lines.append("\\hline")
        lines.append(_render_row(headers))
        lines.append("\\hline")
    else:
        lines.append(_render_row(headers))
        lines.append("\\hline")

    for row in table.rows:
        lines.append(_render_row(row))
        lines.append("\\hline")

    lines.append("\\end{longtable}")
    lines.append("")
    return lines


def _render_group_header(groups: list[tuple[str, int]], total_cols: int) -> str:
    parts: list[str] = []
    cols_used = 0
    for label, span in groups:
        span = max(1, int(span))
        cols_used += span
        parts.append(
            "\\multicolumn{" + str(span) + "}{c|}{" + _latex_escape(label) + "}"
        )
    if cols_used < total_cols:
        parts.append("\\multicolumn{" + str(total_cols - cols_used) + "}{c|}{}")
    return " & ".join(parts) + " \\\\"


def _render_row(cells: list[str]) -> str:
    return " & ".join(_latex_escape(c) for c in cells) + " \\\\"


def _latex_escape(text: str) -> str:
    s = str(text)
    s = s.replace("\\", "\\textbackslash{}").replace("&", "\\&")
    s = s.replace("%", "\\%").replace("$", "\\$")
    s = s.replace("#", "\\#").replace("_", "\\_")
    s = s.replace("{", "\\{").replace("}", "\\}")
    s = (
        s.replace("~", "\\textasciitilde{}")
        .replace("^", "\\textasciicircum{}")
        .replace("ζ", "\\zeta")
    )
    return s


def _latex_preamble(*, title: str | None, root_dir: Path | None) -> str:
    graphic_path = ""
    if root_dir is not None:
        graphic_path = f"\\graphicspath{{{{{root_dir.as_posix()}/}}}}"
    title_line = f"\\title{{{_latex_escape(title)}}}" if title else ""
    return "\n".join(
        [
            "\\documentclass[11pt]{article}",
            "\\usepackage[margin=0.5in]{geometry}",
            "\\usepackage{graphicx}",
            "\\usepackage{float}",
            "\\usepackage{longtable}",
            "\\usepackage{booktabs}",
            "\\usepackage{array}",
            "\\usepackage{newunicodechar}",
            "\\newunicodechar{ζ}{\\zeta}",
            "\\setlength{\\tabcolsep}{3pt}",
            "\\renewcommand{\\arraystretch}{0.9}",
            graphic_path,
            title_line,
        ]
    )
