"""Render a caller's source passages into the markdown the prompt already expects.

List order is the source number. The first item is Source 1. Nothing here sorts or
renumbers. A passage with no title and no author still keeps its number, because a
student can cite it that way.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def source_passage_fields(schema: Mapping[str, Any]) -> list[str]:
    """Caller fields whose items are the ``SourcePassage`` definition."""
    names: list[str] = []
    for name, spec in schema.get("properties", {}).items():
        if not isinstance(spec, Mapping) or spec.get("type") != "array":
            continue
        items = spec.get("items")
        if isinstance(items, Mapping) and items.get("$ref") == "#/$defs/SourcePassage":
            names.append(name)
    return names


def render_source_passages(passages: list[Any]) -> str:
    """The heading style the fixtures already use, one block per passage."""
    return "\n\n".join(_block(index, passage) for index, passage in enumerate(passages, start=1))


def _block(number: int, passage: Mapping[str, Any]) -> str:
    title = passage.get("title")
    author = passage.get("author")
    if title and author:
        heading = f"### Source {number}: {title} — by {author}"
    elif title:
        heading = f"### Source {number}: {title}"
    else:
        heading = f"### Source {number}"
    return f"{heading}\n\n{passage.get('text', '')}"


__all__ = ["render_source_passages", "source_passage_fields"]
