"""Deterministic citation export for registry and literature records.

The website emits four browser-side formats.  This module keeps the same small
metadata contract available to installed-package users without a browser.  It
never fetches or validates bibliographic records; callers remain responsible
for the provenance and correctness of supplied metadata.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

_FORMAT_NAMES = ("BibTeX", "RIS", "Plain", "LaTeX")


def _text(value: Any) -> str:
    return "" if value is None else str(value)


def _required(metadata: Mapping[str, Any], key: str) -> str:
    value = _text(metadata.get(key)).strip()
    if not value:
        raise ValueError(f"citation metadata requires a non-empty {key!r}")
    return value


def _formats(metadata: Mapping[str, Any], *, accessed: str | None = None) -> dict[str, str]:
    key = _required(metadata, "key")
    title = _required(metadata, "title")
    author = _text(metadata.get("author")).strip() or "{GFT Registry}"
    clean_author = author.replace("{", "").replace("}", "")
    year = _text(metadata.get("year")).strip()
    if not year:
        raise ValueError("citation metadata requires a non-empty 'year'")
    url = _text(metadata.get("url")).strip()
    journal = _text(metadata.get("journal")).strip()
    doi = _text(metadata.get("doi")).strip()
    note = _text(metadata.get("note")).strip() or "GFT Registry"
    accessed_text = _text(accessed).strip() if accessed is not None else ""
    accessed_suffix = f", accessed {accessed_text}" if accessed_text else ""

    if journal or doi:
        journal_line = f"\n  journal      = {{{journal}}}," if journal else ""
        doi_line = f"\n  doi          = {{{doi}}}," if doi else ""
        return {
            "BibTeX": (
                f"@article{{{key},\n"
                f"  title        = {{{title}}},\n"
                f"  author       = {{{author}}},{journal_line}\n"
                f"  year         = {{{year}}},{doi_line}\n"
                f"  url          = {{{url}}}\n}}"
            ),
            "RIS": (
                "TY  - JOUR\n"
                f"TI  - {title}\n"
                f"AU  - {clean_author}\n"
                + (f"JO  - {journal}\n" if journal else "")
                + f"PY  - {year}\n"
                + (f"DO  - {doi}\n" if doi else "")
                + f"UR  - {url}\nER  -"
            ),
            "Plain": (
                f"{clean_author}. {title}."
                + (f" {journal}," if journal else "")
                + f" {year}."
                + (f" doi:{doi}." if doi else f" {url}")
                + (f" (accessed {accessed_text})" if accessed_text else "")
            ),
            "LaTeX": (
                f"\\bibitem{{{key}}} {clean_author}, \\emph{{{title}}},"
                + (f" {journal}," if journal else "")
                + f" {year}."
                + (
                    f" \\href{{https://doi.org/{doi}}}{{doi:{doi}}}."
                    if doi
                    else f" \\url{{{url}}}."
                )
            ),
        }

    return {
        "BibTeX": (
            f"@misc{{{key},\n"
            f"  title        = {{{title}}},\n"
            f"  author       = {{{author}}},\n"
            f"  year         = {{{year}}},\n"
            f"  howpublished = {{\\url{{{url}}}}},\n"
            f"  note         = {{{note}{accessed_suffix}}}\n}}"
        ),
        "RIS": (
            "TY  - ELEC\n"
            f"TI  - {title}\n"
            f"AU  - {clean_author}\n"
            f"PY  - {year}\n"
            f"UR  - {url}\n"
            f"N1  - {note}{accessed_suffix}\nER  -"
        ),
        "Plain": (
            f"{clean_author}. {title}. {year}. {url}"
            + (f" (accessed {accessed_text})" if accessed_text else "")
            + "."
        ),
        "LaTeX": (
            f"\\bibitem{{{key}}} {clean_author}, \\emph{{{title}}}, {year}. "
            f"\\url{{{url}}}"
            + (f" (accessed {accessed_text})" if accessed_text else "")
            + "."
        ),
    }


@dataclass(frozen=True, slots=True)
class CitationBundle:
    """All citation representations for one caller-supplied metadata record."""

    key: str
    formats: Mapping[str, str]

    def __post_init__(self) -> None:
        if tuple(self.formats) != _FORMAT_NAMES:
            raise ValueError("citation bundle must contain the four supported formats")

    def to_dict(self) -> dict[str, Any]:
        return {"key": self.key, "formats": dict(self.formats)}

    def __getitem__(self, format_name: str) -> str:
        return self.formats[format_name]


def citation_formats(
    metadata: Mapping[str, Any] | None = None,
    *,
    accessed: str | None = None,
    **fields: Any,
) -> dict[str, str]:
    """Return BibTeX, RIS, plain-text, and LaTeX citation strings.

    ``metadata`` is deliberately a mapping rather than a paper model so this
    operation also covers generated registry entries.  ``accessed`` is explicit
    to keep default output deterministic; no current date is read implicitly.
    """

    if metadata is not None and fields:
        raise TypeError("pass citation metadata either as a mapping or keyword fields")
    values: Mapping[str, Any] = metadata if metadata is not None else fields
    result = _formats(values, accessed=accessed)
    return {name: result[name] for name in _FORMAT_NAMES}


def citation_export(
    metadata: Mapping[str, Any] | None = None,
    *,
    accessed: str | None = None,
    **fields: Any,
) -> CitationBundle:
    """Return a typed citation bundle for one metadata record."""

    values: Mapping[str, Any] = metadata if metadata is not None else fields
    return CitationBundle(
        key=_required(values, "key"),
        formats=citation_formats(values, accessed=accessed),
    )


format_citation = citation_formats

__all__ = ("CitationBundle", "citation_export", "citation_formats", "format_citation")
