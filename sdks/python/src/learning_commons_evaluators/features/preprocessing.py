"""Running one contract-declared computation entry against the input text.

A contract's preprocessing entry names a library and a function under
``implementation.python``; this module dispatches to it. To support a new library, add
one adapter; to support a new ``post_transform`` type, add one handler.
"""

from __future__ import annotations

import math
from collections.abc import Callable

from learning_commons_evaluators.contracts.loader import Implementation, PostTransform


def _textstat_function(function: str) -> Callable[[str], float]:
    import textstat

    fn = getattr(textstat, function, None)
    if not callable(fn):
        raise NotImplementedError(f'Function "{function}" not found in textstat.')
    return fn


def _textstat(function: str, text: str) -> float:
    return float(_textstat_function(function)(text))


#: library -> (resolve the named function, or raise NotImplementedError; call it on text)
_LIBRARY_ADAPTERS: dict[str, tuple[Callable[[str], object], Callable[[str, str], float]]] = {
    "textstat": (_textstat_function, _textstat),
}


def round_half_up(value: float, places: int = 0) -> float:
    """Round half up, as JavaScript's ``Math.round(value * factor) / factor`` does.

    Python's ``round`` is ties-to-even, so ``round(0.125, 2)`` is ``0.12`` where the
    TypeScript SDK computes ``0.13``. This is the SDK's one rounding operation: rounding a
    computed value must mean the same thing wherever it happens, here and in the TypeScript
    SDK, or the same input binds different text. On real ``textstat`` Flesch-Kincaid values
    the two rules disagree about once in 150 inputs, so the choice is not academic.
    """
    factor = 10**places
    return math.floor(value * factor + 0.5) / factor


def _round(value: float, transform: PostTransform) -> float:
    """The contract's ``post_transform: round``, to the precision it declares."""
    return round_half_up(value, transform.precision or 0)


_POST_TRANSFORMS: dict[str, Callable[[float, PostTransform], float]] = {
    "round": _round,
}


def check_implementation(implementation: Implementation) -> None:
    """Fail unless this SDK provides the library, function and transform the entry names.

    Meant for class creation: a contract this SDK cannot run is a gap in the SDK (or the
    registry), not a provider fault, so it must surface at import as
    ``NotImplementedError`` rather than at the first evaluation inside the provider
    error boundary, where it would be misattributed to the model's vendor.

    :raises NotImplementedError: naming the unsupported library, function or transform.
    """
    adapter = _LIBRARY_ADAPTERS.get(implementation.library)
    if adapter is None:
        raise NotImplementedError(
            f'Unsupported preprocessing library "{implementation.library}". '
            f"Supported: {', '.join(_LIBRARY_ADAPTERS)}."
        )
    adapter[0](implementation.function)
    transform = implementation.post_transform
    if transform is not None and transform.type not in _POST_TRANSFORMS:
        raise NotImplementedError(
            f'Unsupported post_transform type "{transform.type}". '
            f"Supported: {', '.join(_POST_TRANSFORMS)}."
        )


def run_preprocessing_step(text: str, implementation: Implementation) -> float:
    """Run a single library computation and its declared post-transform.

    :raises NotImplementedError: for a library, function or transform this SDK does not
        provide (see :func:`check_implementation`, which evaluators call at class creation
        so this never fires during an evaluation).
    """
    check_implementation(implementation)
    result = _LIBRARY_ADAPTERS[implementation.library][1](implementation.function, text)
    if implementation.post_transform is not None:
        result = _POST_TRANSFORMS[implementation.post_transform.type](
            result, implementation.post_transform
        )
    return result


def format_number(value: float) -> str:
    """A computed value as it reaches the prompt.

    Rendered the way JavaScript's ``String(number)`` renders it — ``7`` rather than
    ``7.0`` for an integral value — so the two SDKs bind the same text.
    """
    if float(value).is_integer():
        return str(int(value))
    return repr(float(value))


__all__ = ["check_implementation", "format_number", "round_half_up", "run_preprocessing_step"]
