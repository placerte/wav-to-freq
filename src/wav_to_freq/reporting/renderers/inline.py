from __future__ import annotations

import re

WHITELIST = {"zeta", "ζ", "f", "r2", "snr", "q", "df"}


def render_inline_markdown(text: str) -> str:
    def repl(match: re.Match[str]) -> str:
        base = match.group(1)
        sub = match.group(2)
        if base in {"zeta", "ζ"}:
            return f"ζ_{sub}"
        return f"{base}_{sub}"

    pattern = _subscript_pattern()
    return re.sub(pattern, repl, str(text))


def render_inline_latex(text: str) -> str:
    s = str(text)
    out: list[str] = []
    pattern = re.compile(r"\*\*(.+?)\*\*|" + _subscript_pattern())
    pos = 0
    for match in pattern.finditer(s):
        if match.start() > pos:
            out.append(_latex_escape(s[pos : match.start()]))
        if match.group(1) is not None:
            out.append(f"\\textbf{{{_latex_escape(match.group(1))}}}")
        else:
            base = match.group(2)
            sub = match.group(3)
            if base in {"zeta", "ζ"}:
                base_tex = "\\zeta"
            else:
                base_tex = _latex_escape(base)
            out.append(f"\\ensuremath{{{base_tex}_{{{_latex_escape(sub)}}}}}")
        pos = match.end()
    if pos < len(s):
        out.append(_latex_escape(s[pos:]))
    return "".join(out)


def _subscript_pattern() -> str:
    tokens = "|".join(sorted(WHITELIST, key=len, reverse=True))
    return rf"\b({tokens})_(\w+)\b"


def _latex_escape(text: str) -> str:
    s = str(text)
    s = s.replace("\\", "\\textbackslash{}")
    s = s.replace("&", "\\&")
    s = s.replace("%", "\\%")
    s = s.replace("$", "\\$")
    s = s.replace("#", "\\#")
    s = s.replace("_", "\\_")
    s = s.replace("{", "\\{")
    s = s.replace("}", "\\}")
    s = s.replace("~", "\\textasciitilde{}")
    s = s.replace("^", "\\textasciicircum{}")
    return s
