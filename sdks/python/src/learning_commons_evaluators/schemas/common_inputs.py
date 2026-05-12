"""Common input field types for evaluators.

Each field pairs a typed value with an :class:`~.input_specs.InputSpec` that
describes its constraints.  Validation logic lives on the field; constraint
values live on the spec.  Callers typically obtain a spec from TOML settings
rather than constructing one directly::

    # spec loaded from TOML via EvaluatorMetadata.inputs
    text_spec: TextInputSpec = config.evaluator_metadata.inputs["text"]
    field = TextInputField(spec=text_spec, value="The quick brown fox...")
    field.validate()  # raises ValidationError if constraints are violated
"""

from typing import Any

from learning_commons_evaluators.schemas.errors import ValidationError
from learning_commons_evaluators.schemas.evaluator import InputField
from learning_commons_evaluators.schemas.input_specs import (
    GradeInputSpec,
    TextInputSpec,
)

__all__ = ["GradeInputField", "TextInputField"]


class TextInputField(InputField[str]):
    """Input field for free-form text.

    Narrows :class:`~.evaluator.InputField` to ``value: str`` and
    ``spec: TextInputSpec``.  Free-form text may contain PII, so
    :meth:`input_metadata` returns only the character count — never the raw
    value.

    Constraints (min/max text length) are read from ``spec`` rather than
    stored directly on the field, so the same spec object can be shared across
    many field instances.
    """

    # Narrows the abstract InputField.spec: InputSpec → TextInputSpec.
    # value: str is inherited from InputField[str] and does not need to be redeclared.
    spec: TextInputSpec

    def validate(self) -> None:
        """Raise :class:`~.errors.ValidationError` if the value violates the spec constraints."""
        text_length = len(self.value)
        min_len = self.spec.min_text_length or 0
        if text_length < min_len:
            raise ValidationError(f"Text length {text_length} is below minimum {min_len}.")
        if self.spec.max_text_length is not None and text_length > self.spec.max_text_length:
            raise ValidationError(
                f"Text length {text_length} exceeds maximum {self.spec.max_text_length}."
            )

    def input_metadata(self) -> dict[str, Any]:
        """Return the character count — never the raw text (may contain PII)."""
        return {"textLength": len(self.value)}


class GradeInputField(InputField[int]):
    """Input field for a K–12 grade level (0 = kindergarten, 12 = senior year).

    Narrows :class:`~.evaluator.InputField` to ``value: int`` and
    ``spec: GradeInputSpec``.  The baseline 0–12 range is always enforced;
    ``spec.allowed_grades`` further restricts the valid set when defined.
    """

    # Narrows the abstract InputField.spec: InputSpec → GradeInputSpec.
    # value: int is inherited from InputField[int] and does not need to be redeclared.
    spec: GradeInputSpec

    def validate(self) -> None:
        """Raise :class:`~.errors.ValidationError` if the grade is out of range or not in the allowed set."""
        grade = self.value
        if grade < 0 or grade > 12:
            raise ValidationError(f"Grade {grade} is not in allowed range 0-12.")
        if self.spec.allowed_grades is not None and grade not in self.spec.allowed_grades:
            raise ValidationError(
                f"Grade {grade} is not in allowed set: {sorted(self.spec.allowed_grades)}."
            )

    def input_metadata(self) -> dict[str, Any]:
        """Return grade metadata. Grade is not PII so the value is included directly."""
        return {"grade": self.value}
