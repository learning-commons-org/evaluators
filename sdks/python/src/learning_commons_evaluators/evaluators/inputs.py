"""Validating a caller's inputs against the schema the evaluator declares (SDK spec §4).

Each evaluator's ``input_schema.json`` is the only description of what it accepts, so the
bounds, the accepted grades and the set of field names all come from there. The SDK
applies no defaults of its own.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from learning_commons_evaluators.errors import InputValidationError

#: A validated input: the string the prompt binds, or for an array input (an attached
#: input's file paths) its items, in order.
InputValue = str | tuple[str, ...]


def validate_inputs(inputs: Any, schema: Mapping[str, Any]) -> dict[str, InputValue]:
    """Check ``inputs`` against ``schema`` in the order §4.1 fixes, returning canonical values.

    Fields are visited in declared order — ``required`` first, then any remaining
    properties — so a caller passing two bad inputs always gets the same message, in this
    SDK and in any other reading the same schema.

    Values come back as the strings the prompt binds: an ``int`` passed for an enumerated
    string input such as ``grade_level`` is the idiomatic Python convenience (§2.3) and is
    rendered as its token before the enum check. An array input comes back as a tuple of
    its items, each checked as a string against the array's ``items``.

    :raises InputValidationError: On a non-mapping, an unknown key, a missing field, a
        wrongly typed value, a whitespace-only or out-of-bounds string, a value outside
        a declared ``enum``, or an array input that is not a list of strings or has a count
        outside ``minItems``/``maxItems``.
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

    values: dict[str, InputValue] = {}
    for field in order:
        spec = properties[field]
        value = inputs.get(field)
        if value is None:
            if field in required:
                raise InputValidationError(f"{field} is required.")
            continue
        values[field] = (
            _validate_array(field, value, spec)
            if spec.get("type") == "array"
            else _validate_field(field, value, spec)
        )
    return values


def text_inputs(values: Mapping[str, InputValue]) -> dict[str, str]:
    """The validated inputs that are strings, which are the only ones a prompt can bind.

    For an evaluator whose contract declares no array input this is every input; one that
    attaches files reads its array inputs from the full mapping instead.
    """
    return {name: value for name, value in values.items() if isinstance(value, str)}


def _validate_array(field: str, value: Any, spec: Mapping[str, Any]) -> tuple[str, ...]:
    # A list or a tuple; a bare string is a sequence too, but is exactly the mistake of
    # passing one path where the contract asks for an array of them.
    if not isinstance(value, (list, tuple)):
        raise InputValidationError(f"{field} must be an array.")

    def count(n: int) -> str:
        return f"{n} item{'' if n == 1 else 's'}"

    minimum, maximum = spec.get("minItems"), spec.get("maxItems")
    if minimum is not None and len(value) < minimum:
        raise InputValidationError(
            f"{field} needs at least {count(minimum)}; received {len(value)}."
        )
    if maximum is not None and len(value) > maximum:
        raise InputValidationError(
            f"{field} accepts at most {count(maximum)}; received {len(value)}."
        )
    items = spec.get("items") or {}
    if items.get("type") != "string":
        # A contract fault, not a caller's: the only arrays contracts declare are file paths.
        raise ValueError(
            f"{field} is declared as an array of {items.get('type')}; only arrays of strings "
            "are supported."
        )
    for index, item in enumerate(value):
        where = f"{field}[{index}]"
        if not isinstance(item, str):
            raise InputValidationError(f"{where} must be a string.")
        _validate_string(where, item, items)
    return tuple(value)


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


__all__ = ["InputValue", "primary_text_field", "text_inputs", "validate_inputs"]
