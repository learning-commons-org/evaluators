"""Running one contract-declared computation entry against the input text.

A contract's preprocessing entry names a library and a function under
``implementation.python``; this module dispatches to it. To support a new library, add
one adapter; to support a new ``post_transform`` type, add one handler.
"""

from __future__ import annotations

from collections.abc import Callable

from learning_commons_evaluators.contracts.loader import Implementation, PostTransform


def _textstat(function: str, text: str) -> float:
    import textstat

    fn = getattr(textstat, function, None)
    if not callable(fn):
        raise ValueError(f'Function "{function}" not found in textstat.')
    return float(fn(text))


_LIBRARY_ADAPTERS: dict[str, Callable[[str, str], float]] = {
    "textstat": _textstat,
}


def _round(value: float, transform: PostTransform) -> float:
    return round(value, transform.precision or 0)


_POST_TRANSFORMS: dict[str, Callable[[float, PostTransform], float]] = {
    "round": _round,
}


def run_preprocessing_step(text: str, implementation: Implementation) -> float:
    """Run a single library computation and its declared post-transform.

    :raises ValueError: for a library or transform type this SDK does not provide.
    """
    adapter = _LIBRARY_ADAPTERS.get(implementation.library)
    if adapter is None:
        raise ValueError(
            f'Unsupported preprocessing library "{implementation.library}". '
            f"Supported: {', '.join(_LIBRARY_ADAPTERS)}."
        )
    result = adapter(implementation.function, text)
    if implementation.post_transform is not None:
        transform = _POST_TRANSFORMS.get(implementation.post_transform.type)
        if transform is None:
            raise ValueError(
                f'Unsupported post_transform type "{implementation.post_transform.type}". '
                f"Supported: {', '.join(_POST_TRANSFORMS)}."
            )
        result = transform(result, implementation.post_transform)
    return result


def format_number(value: float) -> str:
    """A computed value as it reaches the prompt.

    Rendered the way JavaScript's ``String(number)`` renders it — ``7`` rather than
    ``7.0`` for an integral value — so the two SDKs bind the same text.
    """
    if float(value).is_integer():
        return str(int(value))
    return repr(float(value))


__all__ = ["format_number", "run_preprocessing_step"]
