"""Tests for input spec types, the INPUT_SPEC_REGISTRY, and AnyInputSpec."""

from typing import Literal, get_args

from learning_commons_evaluators.schemas.input_specs import (
    INPUT_SPEC_REGISTRY,
    AnyInputSpec,
    GradeInputSpec,
    InputSpec,
    TextInputSpec,
    _populate_input_spec_registry,
)


class TestInputSpecRegistry:
    def test_registry_contains_text_input_spec(self):
        assert "TextInputField" in INPUT_SPEC_REGISTRY
        assert INPUT_SPEC_REGISTRY["TextInputField"] is TextInputSpec

    def test_registry_contains_grade_input_spec(self):
        assert "GradeInputField" in INPUT_SPEC_REGISTRY
        assert INPUT_SPEC_REGISTRY["GradeInputField"] is GradeInputSpec

    def test_registry_only_contains_known_keys(self):
        """Guard against accidental additions — update this if a new type is added."""
        assert set(INPUT_SPEC_REGISTRY.keys()) == {"TextInputField", "GradeInputField"}

    def test_new_subclass_is_picked_up_after_repopulation(self):
        """A new InputSpec subclass appears in INPUT_SPEC_REGISTRY after _populate_input_spec_registry().

        This verifies the registry mechanism works end-to-end.  New subclasses must
        also be added to AnyInputSpec manually (see module docstring checklist).
        """

        class _TestInputSpec(InputSpec):
            type: Literal["_TestInputField"] = "_TestInputField"

        try:
            _populate_input_spec_registry()
            assert "_TestInputField" in INPUT_SPEC_REGISTRY
            assert INPUT_SPEC_REGISTRY["_TestInputField"] is _TestInputSpec
        finally:
            # Restore the registry to the canonical state so other tests aren't affected.
            INPUT_SPEC_REGISTRY.pop("_TestInputField", None)
            _populate_input_spec_registry()


class TestAnyInputSpec:
    def test_any_input_spec_includes_text_input_spec(self):
        """AnyInputSpec must include TextInputSpec in its union members."""
        members = get_args(get_args(AnyInputSpec)[0])
        assert TextInputSpec in members

    def test_any_input_spec_includes_grade_input_spec(self):
        """AnyInputSpec must include GradeInputSpec in its union members."""
        members = get_args(get_args(AnyInputSpec)[0])
        assert GradeInputSpec in members


class TestTextInputSpec:
    def test_default_type_discriminator(self):
        spec = TextInputSpec(name="text")
        assert spec.type == "TextInputField"

    def test_optional_length_constraints(self):
        spec = TextInputSpec(name="text", min_text_length=10, max_text_length=1000)
        assert spec.min_text_length == 10
        assert spec.max_text_length == 1000

    def test_no_length_constraints_by_default(self):
        spec = TextInputSpec(name="text")
        assert spec.min_text_length is None
        assert spec.max_text_length is None


class TestGradeInputSpec:
    def test_default_type_discriminator(self):
        spec = GradeInputSpec(name="grade")
        assert spec.type == "GradeInputField"

    def test_optional_allowed_grades(self):
        spec = GradeInputSpec(name="grade", allowed_grades=[3, 4, 5])
        assert spec.allowed_grades == [3, 4, 5]

    def test_no_allowed_grades_by_default(self):
        spec = GradeInputSpec(name="grade")
        assert spec.allowed_grades is None
