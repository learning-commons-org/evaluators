"""Filling a prompt template from a fixed set of placeholder names.

Only declared placeholders are substituted, so an undeclared ``{token}`` in a template is
left alone rather than silently filled from whatever the caller happened to pass. The
names come from the contract. Substitution is plain text replacement of ``{name}``, the
same operation the TypeScript SDK performs, so both SDKs render byte-identical prompts.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping


def render_prompt(template: str, inputs: Mapping[str, str], placeholders: Iterable[str]) -> str:
    text = template
    for name in placeholders:
        if name in inputs:
            text = text.replace(f"{{{name}}}", inputs[name])
    return text


__all__ = ["render_prompt"]
