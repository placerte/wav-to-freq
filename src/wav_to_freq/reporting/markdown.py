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
        # Simple GitHub-flavored markdown table
        self.add("| " + " | ".join(headers) + " |")
        self.add("| " + " | ".join(["---"] * len(headers)) + " |")
        for r in rows:
            self.add("| " + " | ".join(r) + " |")
        self.add()

    def to_markdown(self) -> str:
        # ensure trailing newline
        return "\n".join(self._lines).rstrip() + "\n"
