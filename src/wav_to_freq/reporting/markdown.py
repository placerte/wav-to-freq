from typing import Iterable, Sequence


class MarkdownDoc:
    """
    Tiny helper to build Markdown without a pile of brittle string concatenation.
    Keeps report code readable, while staying dependency-free.
    """

    def __init__(self) -> None:
        self._lines: list[str] = []

    def add(self, line: str = "") -> None:
        self._lines.append(line)

    def h1(self, title: str) -> None:
        self.add(f"# {title}")
        self.add()

    def h2(self, title: str) -> None:
        self.add(f"## {title}")
        self.add()

    def h3(self, title: str) -> None:
        self.add(f"### {title}")
        self.add()

    def p(self, text: str) -> None:
        self.add(text)
        self.add()

    def bullet(self, items: Iterable[str]) -> None:
        for it in items:
            self.add(f"- {it}")
        self.add()

    def codeblock(self, code: str, lang: str = "") -> None:
        self.add(f"```{lang}".rstrip())
        self.add(code.rstrip())
        self.add("```")
        self.add()

    def table(self, headers: Sequence[str], rows: Sequence[Sequence[str]]) -> None:
        def esc(cell: str) -> str:
            # Keep tables structurally valid for Pandoc/GFM
            s = str(cell)
            s = s.replace("\n", "<br>")     # avoid row breaks
            s = s.replace("|", "\\|")       # escape pipe (column delimiter)
            return s

        headers2 = [esc(h) for h in headers]
        self.add("| " + " | ".join(headers2) + " |")
        self.add("| " + " | ".join(["---"] * len(headers2)) + " |")
        for r in rows:
            r2 = [esc(c) for c in r]
            self.add("| " + " | ".join(r2) + " |")
        self.add()

    def to_markdown(self) -> str:
        # ensure trailing newline
        return "\n".join(self._lines).rstrip() + "\n"

    def image(self, path: str, *, alt: str = "", title: str | None = None) -> None:
        """
        Embed an image using Markdown syntax.

        path: relative path from the markdown file
        alt: alt text
        title: optional hover title
        """
        if title:
            self._lines.append(f'![{alt}]({path} "{title}")')
        else:
            self._lines.append(f"![{alt}]({path})")

        self._lines.append("")  # blank line for spacing
