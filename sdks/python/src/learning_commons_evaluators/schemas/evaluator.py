"""Evaluation schemas."""

from abc import ABC, abstractmethod
from typing import Any, ClassVar, Generic, TypeVar

__all__ = [
    "EvaluationAnswer",
    "EvaluationExplanation",
    "EvaluationInput",
    "EvaluationResult",
    "InputField",
]

from pydantic import BaseModel, Field, model_validator

from .errors import ConfigurationError, ValidationError
from .input_specs import InputSpec
from .metadata import EvaluationMetadata

# Type variable for the raw Python value stored in an InputField (str, int, etc.)
_V = TypeVar("_V")


class InputField(BaseModel, Generic[_V], ABC):
    """Abstract base class for all evaluator input fields.

    Pairs a typed ``value`` with an :class:`~.input_specs.InputSpec` that
    describes its constraints.  Subclasses must:

    - Redeclare ``spec`` with the appropriate :class:`~.input_specs.InputSpec`
      subclass to narrow the base type.
    - Provide concrete implementations of :meth:`validate` and
      :meth:`input_metadata`.

    Type parameter:
        _V: The Python type of the raw value (e.g. ``str`` for text fields,
            ``int`` for grade fields).

    Example::

        class TextInputField(InputField[str]):
            spec: TextInputSpec  # narrows InputField.spec: InputSpec

            def validate(self) -> None:
                if len(self.value) < self.spec.min_text_length:
                    raise ValidationError(...)

            def input_metadata(self) -> dict[str, Any]:
                return {"textLength": str(len(self.value))}
    """

    spec: InputSpec
    value: _V

    @abstractmethod
    def validate(self) -> None:
        """Validate *value* against *spec* constraints.

        Raise :class:`~.errors.ValidationError` if the value is invalid.
        """

    @abstractmethod
    def input_metadata(self) -> dict[str, Any]:
        """Return safe, serialisable metadata describing this field.

        Must never expose raw values for fields that may contain PII (e.g. use
        character counts rather than the text itself for free-form text fields).
        """


class EvaluationInput(BaseModel, ABC):
    """Abstract base class for evaluator inputs.

    Concrete subclasses declare their fields as :class:`InputField` subclasses
    and point ``_input_settings`` at the evaluator's settings dict::

        class ConventionalityEvaluationInput(EvaluationInput):
            _input_settings: ClassVar[dict] = _CONVENTIONALITY_CONFIG.evaluator_metadata.inputs

            text: TextInputField
            grade: GradeInputField

            def __init__(self, *, text: str, grade: int, **kwargs):
                super().__init__(text=text, grade=grade, **kwargs)

    The base class :meth:`_coerce_raw_to_input_fields` validator intercepts
    raw Python values before Pydantic field validation, looks up each spec from
    ``_input_settings``, validates the spec type, and constructs the appropriate
    :class:`InputField` instance.  Subclasses only need the minimal
    ``__init__`` above for correct caller-facing type annotations; all
    spec-lookup and construction logic lives here.

    The base class also provides :meth:`validate`, :meth:`input_metadata`, and
    :meth:`input_values` by iterating over every Pydantic model field and
    collecting those that are :class:`InputField` instances.
    """

    _input_settings: ClassVar[dict[str, InputSpec]] = {}
    model_config = {"arbitrary_types_allowed": True}

    @model_validator(mode="before")
    @classmethod
    def _coerce_raw_to_input_fields(cls, data: Any) -> Any:
        """Transform raw Python values into :class:`InputField` instances.

        For each field annotated as an :class:`InputField` subclass, looks up
        the spec from ``cls._input_settings`` and constructs the field.  Raises
        :class:`~.errors.ConfigurationError` if the spec is missing or the wrong
        type.  Non-:class:`InputField` fields and already-constructed
        :class:`InputField` instances are left unchanged.
        """
        if not isinstance(data, dict):
            return data

        out = dict(data)
        for field_name, field_info in cls.model_fields.items():
            annotation = field_info.annotation
            # isinstance(annotation, type) rejects generic aliases like Optional[TextInputField]
            # or Union[TextInputField, None], which Pydantic represents as non-type objects.
            # All current InputField fields are declared as concrete subclasses, so this is safe.
            # If optional InputField fields are ever needed, this guard will need updating.
            if not (isinstance(annotation, type) and issubclass(annotation, InputField)):
                continue  # not a concrete InputField subclass — leave as-is
            if field_name not in out or isinstance(out[field_name], InputField):
                continue  # missing (let Pydantic handle) or already constructed

            spec = cls._input_settings.get(field_name)
            if spec is None:
                raise ConfigurationError(
                    f"Missing input spec for '{field_name}' in {cls.__name__}. "
                    "Check [[evaluator_metadata.inputs]] in evaluator settings."
                )

            expected_spec_type = annotation.model_fields["spec"].annotation
            if not isinstance(expected_spec_type, type):
                raise ConfigurationError(
                    f"Cannot resolve spec type for field '{field_name}' in {cls.__name__}."
                )
            if not isinstance(spec, expected_spec_type):
                raise ConfigurationError(
                    f"Input spec for '{field_name}' in {cls.__name__} has unexpected type "
                    f"{type(spec).__name__!r}; expected {expected_spec_type.__name__}. "
                    "Check [[evaluator_metadata.inputs]] in evaluator settings."
                )

            out[field_name] = annotation(spec=spec, value=out[field_name])

        return out

    def validate(self) -> None:
        """Validate all :class:`InputField` members, collecting every error before raising.

        Raises :class:`~.errors.ValidationError` if any field is invalid.
        """
        errors: list[ValidationError] = []
        for name in type(self).model_fields:
            field_val = getattr(self, name)
            if isinstance(field_val, InputField):
                try:
                    field_val.validate()
                except ValidationError as e:
                    errors.append(e)
        if errors:
            raise ValidationError(f"Validation errors: {errors}")

    def input_metadata(self) -> dict[str, Any]:
        """Return a mapping of field name → :meth:`InputField.input_metadata` for each field.

        Non-:class:`InputField` fields produce a ``None`` entry.
        """
        out: dict[str, Any] = {}
        for name in type(self).model_fields:
            field_val = getattr(self, name)
            if isinstance(field_val, InputField):
                out[name] = field_val.input_metadata()
            else:
                out[name] = None
        return out

    def input_values(self) -> dict[str, Any]:
        """Return a mapping of field name → raw Python value.

        For :class:`InputField` members this is ``field.value``; for any other
        field it is the field value itself.
        """
        out: dict[str, Any] = {}
        for name in type(self).model_fields:
            v = getattr(self, name)
            out[name] = v.value if isinstance(v, InputField) else v
        return out


class EvaluationAnswer(BaseModel):
    """The main answer of an evaluation: score and label."""

    score: Any = Field(
        description="The score of the evaluation. This is typically a string or a number."
    )
    label: str = Field(
        description="The label of the evaluation. This is typically a human-friendly string."
    )


class EvaluationExplanation(BaseModel):
    """Explanation of the evaluation: summary (markdown) and optional keyed details."""

    summary: str = Field(description="A summary of the evaluation in markdown format.")
    details: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional keyed details of the evaluation.",
    )


class EvaluationResult(BaseModel):
    """Standard evaluation result: answer, explanation, and metadata."""

    answer: EvaluationAnswer
    explanation: EvaluationExplanation
    metadata: EvaluationMetadata
