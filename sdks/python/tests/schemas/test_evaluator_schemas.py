"""Tests for EvaluationInput, EvaluationAnswer, EvaluationExplanation, and EvaluationResult."""

from typing import ClassVar

import pytest

from learning_commons_evaluators.evaluators.conventionality import (
    ConventionalityEvaluationInput,
)
from learning_commons_evaluators.schemas.common_inputs import (
    GradeInputField,
    TextInputField,
)
from learning_commons_evaluators.schemas.errors import (
    ConfigurationError,
    ValidationError,
)
from learning_commons_evaluators.schemas.evaluator import (
    EvaluationAnswer,
    EvaluationExplanation,
    EvaluationInput,
    EvaluationResult,
)
from learning_commons_evaluators.schemas.input_specs import (
    GradeInputSpec,
    TextInputSpec,
)
from learning_commons_evaluators.schemas.metadata import (
    Status,
)

# A realistic sample long enough to satisfy the min_text_length=100 constraint.
_SAMPLE_TEXT = (
    "Marco Polo was a Venetian merchant and explorer who traveled through Asia "
    "in the late 13th century. He spent nearly two decades at the court of "
    "Kublai Khan, the Mongol ruler of China, and described his experiences in "
    "a book that introduced Europeans to the Far East."
)


# ---------------------------------------------------------------------------
# A minimal EvaluationInput subclass that mixes a proper InputField with a
# plain float — used to exercise the isinstance(..., InputField) False branches.
# ---------------------------------------------------------------------------

_BARE_TEXT_SPEC = TextInputSpec(name="text")  # no constraints — for testing base-class behaviour


class _MixedInput(EvaluationInput):
    """EvaluationInput with one proper InputField and one plain Python value."""

    text: TextInputField
    weight: float  # no validate(), no input_metadata(), no .value attribute


class TestEvaluationInput:
    # --- happy-path construction, validation, and metadata ---

    def test_validate_and_input_metadata(self):
        inp = ConventionalityEvaluationInput(text=_SAMPLE_TEXT, grade=5)
        inp.validate()
        meta = inp.input_metadata()
        assert meta["text"] == {"textLength": str(len(_SAMPLE_TEXT))}
        assert meta["grade"] == {"grade": 5}

    def test_input_values_returns_primitive_values(self):
        """input_values() should unwrap .value from each InputField."""
        inp = ConventionalityEvaluationInput(text=_SAMPLE_TEXT, grade=7)
        values = inp.input_values()
        assert values["text"] == _SAMPLE_TEXT
        assert values["grade"] == 7

    # --- validation error paths ---

    def test_validate_raises_on_invalid_grade(self):
        inp = ConventionalityEvaluationInput(text=_SAMPLE_TEXT, grade=99)
        with pytest.raises(ValidationError):
            inp.validate()

    def test_validate_raises_on_invalid_text_length(self):
        # min_text_length=100 comes from the TOML settings; "x" is 1 char.
        inp = ConventionalityEvaluationInput(text="x", grade=5)
        with pytest.raises(ValidationError):
            inp.validate()

    def test_validate_collects_all_errors_before_raising(self):
        """All field errors are collected; a single ValidationError is raised at the end."""
        # "x" is below the 100-char minimum; grade 99 is outside the 0-12 range.
        inp = ConventionalityEvaluationInput(text="x", grade=99)
        with pytest.raises(ValidationError) as exc_info:
            inp.validate()
        # Both errors should appear in the combined message.
        msg = str(exc_info.value)
        assert "below minimum" in msg
        assert "0-12" in msg

    # --- isinstance False branches: field without protocol methods ---

    def test_validate_skips_non_inputfield_fields(self):
        """Fields that don't implement the InputField protocol are silently skipped."""
        inp = _MixedInput(text=TextInputField(spec=_BARE_TEXT_SPEC, value="hello"), weight=7.5)
        inp.validate()  # should not raise even though weight is not an InputField

    def test_input_metadata_returns_none_for_non_inputfield_fields(self):
        """Fields that are not InputFields produce a None entry in the output dict."""
        inp = _MixedInput(text=TextInputField(spec=_BARE_TEXT_SPEC, value="hello"), weight=7.5)
        meta = inp.input_metadata()
        assert meta["text"] == {"textLength": "5"}
        assert meta["weight"] is None  # fallback for non-protocol fields

    def test_input_values_returns_field_itself_for_non_inputfield(self):
        """Fields that are not InputFields are returned as-is from input_values()."""
        inp = _MixedInput(text=TextInputField(spec=_BARE_TEXT_SPEC, value="hello"), weight=7.5)
        values = inp.input_values()
        assert values["text"] == "hello"
        assert values["weight"] == 7.5  # not an InputField; the float is returned directly

    # --- InputField subclass isinstance checks ---

    def test_text_input_field_is_inputfield_subclass(self):
        """TextInputField must be an InputField subclass (checked via isinstance)."""
        from learning_commons_evaluators.schemas.evaluator import InputField

        field = TextInputField(spec=_BARE_TEXT_SPEC, value="hello")
        assert isinstance(field, InputField)

    def test_grade_input_field_is_inputfield_subclass(self):
        """GradeInputField must be an InputField subclass (checked via isinstance)."""
        from learning_commons_evaluators.schemas.common_inputs import GradeInputField
        from learning_commons_evaluators.schemas.evaluator import InputField
        from learning_commons_evaluators.schemas.input_specs import GradeInputSpec

        spec = GradeInputSpec(name="grade")
        field = GradeInputField(spec=spec, value=5)
        assert isinstance(field, InputField)

    def test_plain_value_is_not_an_inputfield(self):
        """Plain Python values must not be treated as InputField instances."""
        from learning_commons_evaluators.schemas.evaluator import InputField

        assert not isinstance(7.5, InputField)
        assert not isinstance("raw string", InputField)

    def test_inputfield_cannot_be_instantiated_directly(self):
        """InputField is abstract and must not be instantiable without implementing validate() and input_metadata()."""
        from learning_commons_evaluators.schemas.evaluator import InputField
        from learning_commons_evaluators.schemas.input_specs import TextInputSpec

        with pytest.raises(TypeError, match="abstract"):
            InputField(spec=TextInputSpec(name="text"), value="hello")  # type: ignore[abstract]


class TestCoerceRawToInputFields:
    """Direct unit tests for EvaluationInput._coerce_raw_to_input_fields.

    These tests exercise the model_validator on a minimal concrete subclass
    rather than through a full evaluator, so failures point directly at the
    base-class behaviour rather than evaluator-specific configuration.
    """

    # Minimal concrete EvaluationInput subclass wired to known specs.
    _TEXT_SPEC = TextInputSpec(name="text")
    _GRADE_SPEC = GradeInputSpec(name="grade")

    class _SimpleInput(EvaluationInput):
        _input_settings: ClassVar[dict] = {
            "text": TextInputSpec(name="text"),
            "grade": GradeInputSpec(name="grade"),
        }
        text: TextInputField
        grade: GradeInputField

        def __init__(self, *, text: str, grade: int, **kwargs):
            super().__init__(text=text, grade=grade, **kwargs)

    def test_raw_values_are_wrapped_into_input_fields(self):
        """Raw str/int values should be wrapped into the declared InputField types."""
        inp = self._SimpleInput(text="hello world", grade=5)
        assert isinstance(inp.text, TextInputField)
        assert inp.text.value == "hello world"
        assert isinstance(inp.grade, GradeInputField)
        assert inp.grade.value == 5

    def test_already_constructed_input_field_is_not_rewrapped(self):
        """Passing a fully-constructed InputField instance bypasses construction."""
        pre_built = TextInputField(spec=self._TEXT_SPEC, value="pre-built")
        inp = self._SimpleInput(text=pre_built, grade=3)  # type: ignore[arg-type]
        assert inp.text is pre_built  # same object, not a copy

    def test_non_inputfield_field_is_left_unchanged(self):
        """Plain (non-InputField) fields are passed through without modification."""

        class _WithPlainField(EvaluationInput):
            _input_settings: ClassVar[dict] = {"text": TextInputSpec(name="text")}
            text: TextInputField
            weight: float

            def __init__(self, *, text: str, weight: float, **kwargs):
                super().__init__(text=text, weight=weight, **kwargs)

        inp = _WithPlainField(text="hello", weight=1.5)
        assert inp.weight == 1.5  # plain float, untouched

    def test_missing_spec_raises_configuration_error(self, monkeypatch):
        """ConfigurationError is raised when a required spec is absent from _input_settings."""
        monkeypatch.setattr(self._SimpleInput, "_input_settings", {})
        with pytest.raises(ConfigurationError, match="'text'"):
            self._SimpleInput(text="hello", grade=5)

    def test_wrong_spec_type_raises_configuration_error(self, monkeypatch):
        """ConfigurationError is raised when the spec type doesn't match the field's expectation."""
        monkeypatch.setattr(
            self._SimpleInput,
            "_input_settings",
            {"text": GradeInputSpec(name="text"), "grade": self._GRADE_SPEC},
        )
        with pytest.raises(ConfigurationError, match="TextInputSpec"):
            self._SimpleInput(text="hello", grade=5)

    def test_error_message_includes_class_and_field_name(self, monkeypatch):
        """ConfigurationError messages name both the class and the missing field."""
        monkeypatch.setattr(self._SimpleInput, "_input_settings", {})
        with pytest.raises(ConfigurationError) as exc_info:
            self._SimpleInput(text="hello", grade=5)
        msg = str(exc_info.value)
        assert "_SimpleInput" in msg
        assert "'text'" in msg


class TestEvaluationAnswer:
    def test_score_and_label(self):
        answer = EvaluationAnswer(score="moderately_complex", label="Moderately complex")
        assert answer.score == "moderately_complex"
        assert answer.label == "Moderately complex"


class TestEvaluationExplanation:
    def test_summary_and_details(self):
        explanation = EvaluationExplanation(summary="Reasoning.", details={"key": "value"})
        assert explanation.summary == "Reasoning."
        assert explanation.details["key"] == "value"

    def test_details_defaults_to_empty_dict(self):
        explanation = EvaluationExplanation(summary="Short.")
        assert explanation.details == {}


class TestEvaluationResult:
    def test_construction_and_status(self, evaluation_metadata):
        result = EvaluationResult(
            answer=EvaluationAnswer(score="slightly_complex", label="Slightly complex"),
            explanation=EvaluationExplanation(summary="Summary"),
            metadata=evaluation_metadata,
        )
        assert result.answer.score == "slightly_complex"
        assert result.metadata.status == Status.processing
