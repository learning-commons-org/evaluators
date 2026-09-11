"""Validating a caller's inputs against the schema the evaluator declares (SDK spec §4).

Each evaluator's ``input_schema.json`` is the only description of what it accepts, so the
bounds, the accepted grades and the set of field names all come from there. The SDK
applies no defaults of its own.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from learning_commons_evaluators.errors import InputValidationError


def validate_inputs(inputs: Any, schema: Mapping[str, Any]) -> dict[str, str]:
    """Check ``inputs`` against ``schema`` in the order §4.1 fixes, returning canonical values.

    Fields are visited in declared order — ``required`` first, then any remaining
    properties — so a caller passing two bad inputs always gets the same message, in this
    SDK and in any other reading the same schema.

    Values come back as the strings the prompt binds: an ``int`` passed for an enumerated
    string input such as ``grade_level`` is the idiomatic Python convenience (§2.3) and is
    rendered as its token before the enum check.

    :raises InputValidationError: On a non-mapping, an unknown key, a missing field, a
        wrongly typed value, a whitespace-only or out-of-bounds string, or a value outside
        a declared ``enum``.
    """
    if not isinstance(inputs, Mapping):
        raise InputValidationError(
            f"Expected a mapping of inputs, received {type(inputs).__name__}."
        )

    properties: Mapping[str, Mapping[str, Any]] = schema.get("properties", {})
    declared = list(properties)

    # Contracts declare ``additionalProperties: false``, so an unexpected key is a caller
    # mistake worth naming rather than something to quietly drop.
    for key in inputs:
        if key not in declared:
            raise InputValidationError(
                f'Unknown input "{key}". This evaluator accepts: {", ".join(declared)}.'
            )

    required = list(schema.get("required", []))
    order = [*required, *(f for f in declared if f not in required)]

    values: dict[str, str] = {}
    for field in order:
        spec = properties[field]
        value = inputs.get(field)
        if value is None:
            if field in required:
                raise InputValidationError(f"{field} is required.")
            continue
        values[field] = _validate_field(field, value, spec)
    return values


def _validate_field(field: str, value: Any, spec: Mapping[str, Any]) -> str:
    kind = spec.get("type")
    if kind == "string":
        if isinstance(value, bool) or not isinstance(value, (str, int)):
            raise InputValidationError(f"{field} must be a string.")
        if isinstance(value, int):
            if "enum" not in spec:
                raise InputValidationError(f"{field} must be a string.")
            value = str(value)
        _validate_string(field, value, spec)
        return value
    if kind == "integer":
        if isinstance(value, bool) or not isinstance(value, int):
            raise InputValidationError(f"{field} must be an integer.")
        minimum, maximum = spec.get("minimum"), spec.get("maximum")
        if minimum is not None and value < minimum:
            raise InputValidationError(f"{field} must be at least {minimum}.")
        if maximum is not None and value > maximum:
            raise InputValidationError(f"{field} must be at most {maximum}.")
        return str(value)
    return str(value)


def _validate_string(field: str, value: str, spec: Mapping[str, Any]) -> None:
    accepted = spec.get("enum")
    if accepted is not None:
        if value not in accepted:
            raise InputValidationError(
                f'Invalid {field} "{value}". Accepted values: {", ".join(map(str, accepted))}.'
            )
        return

    # Trimming decides whether the value is blank and nothing more: the bounds below
    # measure the string as the caller sent it, which is also what reaches the model.
    if not value.strip():
        raise InputValidationError(f"{field} cannot be empty or contain only whitespace")

    minimum, maximum = spec.get("minLength"), spec.get("maxLength")
    if minimum is not None and len(value) < minimum:
        raise InputValidationError(f"{field} is too short. Minimum length is {minimum} characters.")
    if maximum is not None and len(value) > maximum:
        raise InputValidationError(f"{field} is too long. Maximum length is {maximum} characters.")


def primary_text_field(schema: Mapping[str, Any]) -> str | None:
    """The field a log line or telemetry treats as the primary text.

    The wire still carries one text length, so an evaluator with two texts has to pick
    one: the first declared string input that is not an enum.
    """
    for name, spec in schema.get("properties", {}).items():
        if spec.get("type") == "string" and "enum" not in spec:
            return name
    return None


__all__ = ["primary_text_field", "validate_inputs"]
