"""Input spec types describing the constraints for evaluator input fields.

A spec is defined once — in the evaluator's settings TOML — and attached to
its corresponding field when the input object is constructed.

Hierarchy::

    InputSpec          base: name, type, description, required
    ├─ TextInputSpec   adds: min_text_length, max_text_length, strip_whitespace
    └─ GradeInputSpec  adds: allowed_grades

**Adding a new input spec type — checklist**

1. Define a new subclass of :class:`InputSpec` in *this file* with a
   ``type: Literal["YourFieldType"]`` default.  The registry is rebuilt
   automatically via :func:`_populate_input_spec_registry`.
2. Add the new class to the explicit :data:`AnyInputSpec` union below
   (required — ``AnyInputSpec`` is not rebuilt automatically).
3. Add the matching ``InputField`` concrete class in ``common_inputs.py``.
4. Run ``make generate-settings`` (from the ``sdks/python/`` directory) after
   updating any TOML that uses the new type.
"""

from collections.abc import Iterator
from typing import Annotated, Literal

from pydantic import BaseModel, Field
from pydantic_core import PydanticUndefined

__all__ = [
    "AnyInputSpec",
    "GradeInputSpec",
    "INPUT_SPEC_REGISTRY",
    "InputSpec",
    "TextInputSpec",
]

# ---------------------------------------------------------------------------
# Registry: populated by _populate_input_spec_registry() after subclasses exist
# ---------------------------------------------------------------------------

# Maps the ``type`` discriminator string to the concrete InputSpec class.
# Used by the TOML parser to instantiate the right subclass and to build
# the AnyInputSpec discriminated union below.
INPUT_SPEC_REGISTRY: dict[str, type["InputSpec"]] = {}


# ---------------------------------------------------------------------------
# Base and concrete spec classes
# ---------------------------------------------------------------------------


class InputSpec(BaseModel):
    """Base spec for one evaluator input field.

    Identifies the field (``name``, ``type``) and carries optional metadata
    (``description``, ``required``).  Subclasses add type-specific constraints.
    """

    name: str
    type: str
    description: str = ""
    required: bool = True


class TextInputSpec(InputSpec):
    """Spec for a text input field.

    Constraint fields are optional; omitting them means no length limit is
    enforced for that boundary.

    When ``strip_whitespace`` is true (the default), leading and trailing whitespace is removed
    from the value when a :class:`~.common_inputs.TextInputField` is constructed
    (before length validation). Set it to false to keep the raw string unchanged.
    """

    type: Literal["TextInputField"] = "TextInputField"
    min_text_length: int | None = None
    max_text_length: int | None = None
    strip_whitespace: bool = True


class GradeInputSpec(InputSpec):
    """Spec for a grade input field.

    When ``allowed_grades`` is set, only those values pass validation in
    addition to the field's baseline 0–12 range check.
    """

    type: Literal["GradeInputField"] = "GradeInputField"
    allowed_grades: list[int] | None = None


def _discriminated_input_spec_subclasses(
    base: type[InputSpec],
) -> Iterator[type[InputSpec]]:
    """Descendants of ``base`` that define a string ``type`` default (discriminator value)."""
    for cls in base.__subclasses__():
        yield from _discriminated_input_spec_subclasses(cls)
        tf = cls.model_fields.get("type")
        if tf is None or tf.is_required():
            continue
        d = tf.default
        if d is PydanticUndefined or not isinstance(d, str):
            continue
        yield cls


def _populate_input_spec_registry() -> None:
    """Fill :data:`INPUT_SPEC_REGISTRY` once concrete InputSpec models exist."""
    INPUT_SPEC_REGISTRY.clear()
    for cls in _discriminated_input_spec_subclasses(InputSpec):
        key = cls.model_fields["type"].default
        assert isinstance(key, str)  # guarded by _discriminated_input_spec_subclasses
        INPUT_SPEC_REGISTRY[key] = cls


_populate_input_spec_registry()

# ---------------------------------------------------------------------------
# AnyInputSpec — explicit union; update this when adding a new InputSpec subclass
# ---------------------------------------------------------------------------

# NOTE: This union is intentionally explicit rather than built dynamically from
# INPUT_SPEC_REGISTRY.  Dynamic unions are opaque to static type checkers and IDEs.
# When you add a new InputSpec subclass, add it here too (see the module docstring
# for the full checklist).
AnyInputSpec = Annotated[
    TextInputSpec | GradeInputSpec,
    Field(discriminator="type"),
]
