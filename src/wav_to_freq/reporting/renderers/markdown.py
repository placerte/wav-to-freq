from __future__ import annotations

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
from wav_to_freq.reporting.renderers.inline import render_inline_markdown


def render_markdown(doc: ReportDoc) -> str:
    lines: list[str] = []

    for node in doc.nodes:
        lines.extend(_render_node(node))

    return "\n".join(lines).rstrip() + "\n"


def _render_node(node: DocNode) -> list[str]:
    if isinstance(node, Heading):
        prefix = "#" * max(1, min(6, int(node.level)))
        return [f"{prefix} {render_inline_markdown(node.text)}", ""]
    if isinstance(node, Paragraph):
        return [render_inline_markdown(node.text), ""]
    if isinstance(node, BulletList):
        return [f"- {render_inline_markdown(item)}" for item in node.items] + [""]
    if isinstance(node, CodeBlock):
        return [f"```{node.lang}".rstrip(), node.code.rstrip(), "```", ""]
    if isinstance(node, Image):
        alt = render_inline_markdown(node.alt)
        if node.title:
            title = render_inline_markdown(node.title)
            return [f'![{alt}]({node.path} "{title}")', ""]
        return [f"![{alt}]({node.path})", ""]
    if isinstance(node, Table):
        return _render_table(node)
    return []


def _render_table(table: Table) -> list[str]:
    headers = _flatten_headers(table.headers, table.header_groups)
    lines = ["| " + " | ".join(_esc(h) for h in headers) + " |"]
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for row in table.rows:
        lines.append("| " + " | ".join(_esc(c) for c in row) + " |")
    lines.append("")
    return lines


def _flatten_headers(
    headers: list[str], header_groups: list[tuple[str, int]] | None
) -> list[str]:
    if not header_groups:
        return headers

    flat: list[str] = []
    idx = 0
    for label, span in header_groups:
        for _ in range(span):
            if idx >= len(headers):
                break
            suffix = headers[idx]
            idx += 1
            if label:
                flat.append(f"{label} {suffix}".strip())
            else:
                flat.append(suffix)
    flat.extend(headers[idx:])
    return flat


def _esc(cell: str) -> str:
    s = render_inline_markdown(str(cell))
    s = s.replace("\n", "<br>")
    s = s.replace("|", "\\|")
    return s
