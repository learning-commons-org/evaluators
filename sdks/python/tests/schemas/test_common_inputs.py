"""Tests for TextInputField and GradeInputField."""

import pytest

from learning_commons_evaluators.schemas.common_inputs import (
    GradeInputField,
    TextInputField,
)
from learning_commons_evaluators.schemas.errors import InputValidationError
from learning_commons_evaluators.schemas.input_specs import (
    GradeInputSpec,
    TextInputSpec,
)

# ---------------------------------------------------------------------------
# Helpers: minimal specs for tests that don't exercise constraints
# ---------------------------------------------------------------------------


def _text_spec(**kwargs) -> TextInputSpec:
    """Return a TextInputSpec with no constraints unless overridden."""
    return TextInputSpec(name="text", **kwargs)


def _grade_spec(**kwargs) -> GradeInputSpec:
    """Return a GradeInputSpec with no constraints unless overridden."""
    return GradeInputSpec(name="grade", **kwargs)


class TestTextInputField:
    def test_value_and_metadata(self):
        field = TextInputField(spec=_text_spec(), value="Hello, world!")
        assert field.value == "Hello, world!"
        assert field.input_metadata() == {"textLength": 13}

    def test_validate_passes_within_limits(self):
        TextInputField(
            spec=_text_spec(min_text_length=2, max_text_length=10),
            value="Hello",
        ).validate()

    def test_validate_passes_at_exact_min(self):
        TextInputField(spec=_text_spec(min_text_length=2), value="ab").validate()

    def test_validate_raises_below_min(self):
        with pytest.raises(InputValidationError, match="below minimum"):
            TextInputField(spec=_text_spec(min_text_length=2), value="a").validate()

    def test_validate_passes_at_exact_max(self):
        TextInputField(spec=_text_spec(max_text_length=10), value="a" * 10).validate()

    def test_validate_raises_above_max(self):
        with pytest.raises(InputValidationError, match="exceeds maximum"):
            TextInputField(spec=_text_spec(max_text_length=10), value="a" * 11).validate()

    def test_validate_no_max_by_default(self):
        # A spec with no constraints should accept arbitrarily long text.
        TextInputField(spec=_text_spec(), value="x" * 1000).validate()

    def test_spec_is_accessible(self):
        spec = _text_spec(min_text_length=50)
        field = TextInputField(spec=spec, value="abc")
        assert field.spec.min_text_length == 50

    def test_strip_whitespace_false_preserves_padding(self):
        field = TextInputField(spec=_text_spec(strip_whitespace=False), value="  ab  ")
        assert field.value == "  ab  "

    def test_strip_whitespace_true_trims_value_by_default(self):
        field = TextInputField(spec=_text_spec(), value="  ab  ")
        assert field.value == "ab"

    def test_strip_whitespace_applies_before_length_validation(self):
        TextInputField(
            spec=_text_spec(min_text_length=2),
            value="  xx  ",
        ).validate()

    def test_strip_whitespace_explicit_true_trims_value(self):
        field = TextInputField(
            spec=_text_spec(strip_whitespace=True),
            value="  cd  ",
        )
        assert field.value == "cd"

    def test_validate_raises_when_strip_shortens_below_min(self):
        """Padding does not count toward ``min_text_length`` when stripping is on."""
        with pytest.raises(InputValidationError, match="below minimum"):
            TextInputField(
                spec=_text_spec(min_text_length=5, strip_whitespace=True),
                value="  ab  ",
            ).validate()


class TestGradeInputField:
    def test_value_and_metadata(self):
        field = GradeInputField(spec=_grade_spec(), value=5)
        assert field.value == 5
        assert field.input_metadata() == {"grade": 5}

    def test_validate_passes_at_boundaries(self):
        GradeInputField(spec=_grade_spec(), value=0).validate()  # lower boundary
        GradeInputField(spec=_grade_spec(), value=12).validate()  # upper boundary

    def test_validate_raises_below_0(self):
        with pytest.raises(InputValidationError, match="0-12"):
            GradeInputField(spec=_grade_spec(), value=-1).validate()

    def test_validate_raises_above_12(self):
        with pytest.raises(InputValidationError, match="0-12"):
            GradeInputField(spec=_grade_spec(), value=13).validate()

    def test_validate_passes_when_in_allowed_grades(self):
        GradeInputField(
            spec=_grade_spec(allowed_grades=[5, 6, 7]),
            value=6,
        ).validate()

    def test_validate_raises_when_not_in_allowed_grades(self):
        with pytest.raises(InputValidationError, match="not in allowed set"):
            GradeInputField(
                spec=_grade_spec(allowed_grades=[5, 6, 7]),
                value=8,
            ).validate()

    def test_spec_is_accessible(self):
        spec = _grade_spec(allowed_grades=[3, 4, 5])
        field = GradeInputField(spec=spec, value=4)
        assert field.spec.allowed_grades == [3, 4, 5]
