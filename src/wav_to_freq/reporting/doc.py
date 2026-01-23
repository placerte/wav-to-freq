from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence


@dataclass(frozen=True)
class Heading:
    level: int
    text: str


@dataclass(frozen=True)
class Paragraph:
    text: str


@dataclass(frozen=True)
class BulletList:
    items: list[str]


@dataclass(frozen=True)
class CodeBlock:
    code: str
    lang: str = ""


@dataclass(frozen=True)
class Image:
    path: str
    alt: str = ""
    title: str | None = None


@dataclass(frozen=True)
class Table:
    headers: list[str]
    rows: list[list[str]]
    header_groups: list[tuple[str, int]] | None = None


DocNode = Heading | Paragraph | BulletList | CodeBlock | Image | Table


class ReportDoc:
    """Format-agnostic report document."""

    def __init__(self) -> None:
        self._nodes: list[DocNode] = []

    @property
    def nodes(self) -> Sequence[DocNode]:
        return tuple(self._nodes)

    def h1(self, text: str) -> None:
        self._nodes.append(Heading(level=1, text=text))

    def h2(self, text: str) -> None:
        self._nodes.append(Heading(level=2, text=text))

    def h3(self, text: str) -> None:
        self._nodes.append(Heading(level=3, text=text))

    def h4(self, text: str) -> None:
        self._nodes.append(Heading(level=4, text=text))

    def p(self, text: str) -> None:
        self._nodes.append(Paragraph(text=text))

    def bullet(self, items: Iterable[str]) -> None:
        self._nodes.append(BulletList(items=list(items)))

    def codeblock(self, code: str, lang: str = "") -> None:
        self._nodes.append(CodeBlock(code=code, lang=lang))

    def image(self, path: str, *, alt: str = "", title: str | None = None) -> None:
        self._nodes.append(Image(path=path, alt=alt, title=title))

    def table(
        self,
        headers: Sequence[str],
        rows: Sequence[Sequence[str]],
        *,
        header_groups: Sequence[tuple[str, int]] | None = None,
    ) -> None:
        self._nodes.append(
            Table(
                headers=list(headers),
                rows=[list(r) for r in rows],
                header_groups=list(header_groups) if header_groups else None,
            )
        )
