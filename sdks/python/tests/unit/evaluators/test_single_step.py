"""The single-step flow, tested on a synthetic contract so every branch is reachable."""

from __future__ import annotations

import asyncio
import copy
import io
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from unittest.mock import patch

import httpx2
import openai
import pytest
import textstat
from PIL import Image
from pydantic import BaseModel, Field

from learning_commons_evaluators import (
    AuthenticationError,
    ConfigurationError,
    EvaluationResult,
    InputValidationError,
    LLMOutputProcessingError,
    ModelOverride,
    Provider,
    read_outcome,
)
from learning_commons_evaluators.contracts.loader import Contract
from learning_commons_evaluators.evaluators.single_step import (
    SingleStepEvaluator,
    attachments_of,
)
from learning_commons_evaluators.features import image_source
from learning_commons_evaluators.features.image_source import ImageBounds
from learning_commons_evaluators.providers import LLMResponse, ProviderConfig, TokenUsage
from tests.unit.conftest import FakeProvider, ProviderFactory

STABLE_ID = "11111111-1111-1111-1111-111111111111"


def contract(**overrides: Any) -> Contract:
    raw: dict[str, Any] = {
        "evaluator": {
            "id": "demo.area.thing",
            "stable_id": STABLE_ID,
            "id_history": ["demo.area.old_thing"],
            "name": "Thing Evaluator",
            "description": "Demonstration contract.",
            # Deliberately wider than the input enum, which is the only way to tell which
            # of the two the class read.
            "supported_grades": ["3", "4", "5", "6"],
        },
        "input_schema": {
            "type": "object",
            "required": ["text", "grade_level"],
            "additionalProperties": False,
            "properties": {
                "text": {"type": "string", "minLength": 1},
                "grade_level": {"type": "string", "enum": ["3", "4", "5"]},
            },
        },
        "output_schema": {
            "type": "object",
            "required": ["verdict", "reasoning"],
            "properties": {"verdict": {"type": "string"}, "reasoning": {"type": "string"}},
        },
        "preprocessing": [
            {
                "id": "fk_score",
                "type": "computation",
                "kind": "flesch_kincaid_grade",
                "input": "text",
                "output": "fk_score",
                "implementation": {
                    "python": {
                        "library": "textstat",
                        "function": "flesch_kincaid_grade",
                        "post_transform": {"type": "round", "precision": 2},
                    }
                },
            }
        ],
        "steps": [
            {
                "id": "evaluate_thing",
                "type": "llm",
                "prompt": {
                    "messages": [
                        {"role": "system", "source_path": "system.txt"},
                        {"role": "user", "source_path": "user.txt"},
                    ],
                    "placeholders": {
                        "text": {"required": True, "source": "input"},
                        "grade_level": {"required": True, "source": "input"},
                        "fk_score": {"required": True, "source": "preprocessing.fk_score"},
                    },
                },
                "model": {"provider": "google", "name": "gemini-3-flash-preview"},
                "generation": {"temperature": 0.5},
                "parser": {"kind": "structured_output"},
            }
        ],
        "outcome": {"score": "verdict", "reasoning": "reasoning"},
        "documents": {
            "system.txt": "system: {text} at {grade_level} with {fk_score} {undeclared}",
            "user.txt": "user: {text} at {grade_level} with {fk_score}",
        },
    }
    raw.update(overrides)
    return Contract.model_validate(raw)


class ThingOutput(BaseModel):
    verdict: str
    reasoning: str


class ThingInput(BaseModel):
    text: str
    grade_level: int


def define(**overrides: Any) -> type[SingleStepEvaluator[ThingInput, ThingOutput]]:
    class ThingEvaluator(SingleStepEvaluator[ThingInput, ThingOutput]):
        contract = globals()["contract"](**overrides)
        input_model = ThingInput
        output_model = ThingOutput

    return ThingEvaluator


INPUT = {"text": "The cat sat on the mat.", "grade_level": "4"}
FK = textstat.flesch_kincaid_grade(INPUT["text"])


def _verdict(schema: type[BaseModel]) -> BaseModel:
    return schema.model_validate({"verdict": "clear", "reasoning": "because"})


@pytest.fixture
def providers() -> Any:
    from unittest.mock import patch

    factory = ProviderFactory(payload=_verdict)
    with patch("learning_commons_evaluators.evaluators.base.create_provider", factory):
        yield factory


class TestRefusesAContractItCannotRun:
    def test_names_the_step_the_convention_expects(self) -> None:
        steps = [
            {
                "id": "not_the_convention",
                "type": "llm",
                "model": {"provider": "google", "name": "m"},
                "prompt": {"messages": [], "placeholders": {}},
                "generation": {"temperature": 0},
                "parser": {"kind": "structured_output"},
            }
        ]
        with pytest.raises(LookupError, match='Step "evaluate_thing" not found in Thing Evaluator'):
            define(steps=steps)

    def test_refuses_a_contract_with_more_than_one_step(self) -> None:
        raw = contract().model_dump(by_alias=True)
        second = {**raw["steps"][0], "id": "second_call"}
        with pytest.raises(
            ValueError, match="declares 2 step\\(s\\); SingleStepEvaluator runs exactly one"
        ):
            define(steps=[raw["steps"][0], second])

    def test_refuses_an_optional_only_step(self) -> None:
        raw = contract().model_dump(by_alias=True)
        raw["steps"][0]["optional"] = True
        with pytest.raises(ValueError, match="exactly one non-optional step"):
            define(steps=raw["steps"])

    def test_refuses_a_placeholder_that_reads_another_step(self) -> None:
        raw = contract().model_dump(by_alias=True)
        raw["steps"][0]["prompt"]["placeholders"]["extra"] = {
            "required": True,
            "source": "steps.other.output",
        }
        with pytest.raises(ValueError, match="reads another step"):
            define(**{k: raw[k] for k in ("steps",)})

    @pytest.mark.parametrize(
        ("patch", "message"),
        [
            ({"library": "nltk"}, 'Unsupported preprocessing library "nltk"'),
            ({"function": "nope"}, 'Function "nope" not found in textstat'),
            ({"post_transform": {"type": "floor"}}, 'Unsupported post_transform type "floor"'),
        ],
        ids=["library", "function", "transform"],
    )
    def test_refuses_preprocessing_this_sdk_cannot_run_at_class_creation(
        self, patch: dict[str, Any], message: str
    ) -> None:
        # Our gap, not the provider's: it must never reach evaluate(), where the error
        # boundary would attribute it to the model's vendor as an LLMProviderError.
        raw = contract().model_dump(by_alias=True)
        raw["preprocessing"][0]["implementation"]["python"].update(patch)
        with pytest.raises(
            NotImplementedError, match=f'Preprocessing "fk_score" in Thing Evaluator.*{message}'
        ):
            define(preprocessing=raw["preprocessing"])

    def test_refuses_preprocessing_without_a_python_computation(self) -> None:
        entry = {
            "id": "x",
            "type": "computation",
            "kind": "custom",
            "input": "text",
            "output": "x",
            "implementation": {"typescript": {"library": "l", "function": "f"}},
        }
        with pytest.raises(ValueError, match='Preprocessing "x".*no Python computation'):
            define(preprocessing=[entry])


class TestReadsBehaviourFromTheContract:
    def test_metadata(self) -> None:
        metadata = define().metadata
        assert metadata.id == "demo.area.thing"
        assert metadata.stable_id == STABLE_ID
        assert metadata.id_history == ("demo.area.old_thing",)
        assert metadata.name == "Thing Evaluator"
        assert metadata.supported_grades == ("3", "4", "5", "6")
        assert metadata.default_providers == (Provider.GOOGLE,)
        assert metadata.required_credentials == ()
        assert metadata.outcome is not None and metadata.outcome.score == "verdict"

    def test_builds_the_provider_the_step_declares(self, providers: ProviderFactory) -> None:
        define()(google_api_key="k", max_retries=1)
        config = providers.last.config
        assert (config.type, config.model, config.api_key, config.max_retries) == (
            Provider.GOOGLE,
            "gemini-3-flash-preview",
            "k",
            1,
        )

    async def test_sends_the_temperature_and_schema_the_contract_declares(
        self, providers: ProviderFactory
    ) -> None:
        await define()(google_api_key="k").evaluate(**INPUT)
        call = providers.last.calls[0]
        assert call["temperature"] == 0.5
        assert call["schema"] is ThingOutput

    async def test_an_override_does_not_carry_the_contracts_temperature_across(
        self, providers: ProviderFactory
    ) -> None:
        # The contract pins 0.5 for its own model; an override replaces the model, and
        # whether that model accepts a temperature at all is a property of the model.
        override = ModelOverride(provider=Provider.ANTHROPIC, model="claude-opus-5")
        await define()(anthropic_api_key="a", model_override=override).evaluate(**INPUT)
        assert providers.last.calls[0]["temperature"] is None

    async def test_renders_prompts_with_declared_placeholders_only(
        self, providers: ProviderFactory
    ) -> None:
        await define()(google_api_key="k").evaluate(**INPUT)
        messages = providers.last.calls[0]["messages"]
        fk = str(round(FK, 2)) if not round(FK, 2).is_integer() else str(int(round(FK, 2)))
        assert messages[0] == {
            "role": "system",
            "content": f"system: The cat sat on the mat. at 4 with {fk} {{undeclared}}",
        }
        assert messages[1] == {
            "role": "user",
            "content": f"user: The cat sat on the mat. at 4 with {fk}",
        }

    async def test_a_conditional_preprocessing_entry_only_runs_when_its_condition_holds(
        self, providers: ProviderFactory
    ) -> None:
        raw = contract().model_dump(by_alias=True)
        raw["preprocessing"][0]["condition"] = {"input": "grade_level", "in": ["3"]}
        raw["steps"][0]["prompt"]["placeholders"]["fk_score"]["required"] = False
        evaluator = define(preprocessing=raw["preprocessing"], steps=raw["steps"])(
            google_api_key="k"
        )
        await evaluator.evaluate(**INPUT)
        assert "{fk_score}" in providers.last.calls[0]["messages"][1]["content"]


class TestInputs:
    async def test_accepts_the_input_model_and_an_int_grade(
        self, providers: ProviderFactory
    ) -> None:
        await define()(google_api_key="k").evaluate(ThingInput(text="Hello there.", grade_level=4))
        assert " at 4 with" in providers.last.calls[0]["messages"][1]["content"]

    async def test_accepts_keyword_fields_with_an_int_grade(
        self, providers: ProviderFactory
    ) -> None:
        await define()(google_api_key="k").evaluate(text="Hello there.", grade_level=5)
        assert " at 5 with" in providers.last.calls[0]["messages"][1]["content"]

    async def test_rejects_both_forms_at_once(self, providers: ProviderFactory) -> None:
        with pytest.raises(TypeError, match="not both"):
            await define()(google_api_key="k").evaluate(
                ThingInput(text="t", grade_level=4), text="t"
            )

    @pytest.mark.parametrize(
        ("inputs", "message"),
        [
            ({"text": "t"}, "grade_level is required."),
            ({**INPUT, "grade_level": "6"}, 'Invalid grade_level "6". Accepted values: 3, 4, 5.'),
            ({**INPUT, "extra": 1}, 'Unknown input "extra"'),
            ({**INPUT, "text": "  "}, "text cannot be empty"),
        ],
    )
    async def test_validation_happens_before_any_call(
        self, providers: ProviderFactory, inputs: dict[str, Any], message: str
    ) -> None:
        evaluator = define()(google_api_key="k")
        with pytest.raises(InputValidationError, match=message):
            await evaluator.evaluate(**inputs)
        assert providers.last.calls == []

    def test_grades_are_validated_against_the_input_enum_not_supported_grades(
        self, providers: ProviderFactory
    ) -> None:
        # supported_grades says 6; the input schema does not. The schema decides (§4.2).
        with pytest.raises(InputValidationError, match='Invalid grade_level "6"'):
            define()(google_api_key="k").evaluate_sync(text="Hello there.", grade_level=6)


class TestEnvelope:
    async def test_three_fields(self, providers: ProviderFactory) -> None:
        evaluation = await define()(google_api_key="k").evaluate(**INPUT)
        assert isinstance(evaluation, EvaluationResult)
        assert evaluation.evaluator == "demo.area.thing"
        assert evaluation.result == ThingOutput(verdict="clear", reasoning="because")
        assert evaluation.metadata.model == "google:gemini-3-flash-preview"
        assert evaluation.metadata.token_usage.input_tokens == 7
        assert evaluation.metadata.token_usage.output_tokens == 3
        assert evaluation.metadata.processing_time_ms >= 0

    async def test_the_model_reflects_an_override(self, providers: ProviderFactory) -> None:
        override = ModelOverride(provider=Provider.OPENAI, model="gpt-4o-2024-11-20")
        evaluator = define()(openai_api_key="o", model_override=override)
        evaluation = await evaluator.evaluate(**INPUT)
        assert evaluation.metadata.model == "openai:gpt-4o-2024-11-20"

    async def test_read_outcome_reads_the_declared_fields(self, providers: ProviderFactory) -> None:
        evaluator = define()(google_api_key="k")
        evaluation = await evaluator.evaluate(**INPUT)
        outcome = read_outcome(evaluation, evaluator.metadata.outcome)
        assert (outcome.score, outcome.reasoning) == ("clear", "because")

    def test_evaluate_sync(self, providers: ProviderFactory) -> None:
        assert define()(google_api_key="k").evaluate_sync(**INPUT).result.verdict == "clear"

    async def test_evaluate_sync_refuses_a_running_loop(self, providers: ProviderFactory) -> None:
        with pytest.raises(RuntimeError, match="await evaluator.evaluate"):
            define()(google_api_key="k").evaluate_sync(**INPUT)


class TestLifecycle:
    """``aclose``/``close`` are a no-op here, and that is the contract worth pinning.

    An evaluator that owns a dependency client — the Knowledge Graph one owns a
    connection pool — overrides ``aclose``. Every other evaluator inherits these, so
    closing is one habit for callers rather than a per-evaluator question.
    """

    async def test_aclose_is_a_no_op_and_repeatable(self, providers: ProviderFactory) -> None:
        evaluator = define()(google_api_key="k")
        await evaluator.aclose()
        await evaluator.aclose()
        # Still usable: closing something that owns nothing releases nothing.
        assert (await evaluator.evaluate(**INPUT)).result.verdict == "clear"

    async def test_async_context_manager_yields_the_evaluator(
        self, providers: ProviderFactory
    ) -> None:
        evaluator = define()(google_api_key="k")
        async with evaluator as entered:
            assert entered is evaluator

    def test_close_runs_aclose(self, providers: ProviderFactory) -> None:
        closed: list[str] = []

        class Closing(define()):  # type: ignore[misc]
            async def aclose(self) -> None:
                closed.append("yes")

        Closing(google_api_key="k").close()
        assert closed == ["yes"]

    async def test_close_refuses_a_running_loop(self, providers: ProviderFactory) -> None:
        with pytest.raises(RuntimeError, match="await evaluator.aclose"):
            define()(google_api_key="k").close()


class TestFailures:
    async def test_provider_failures_are_classified_and_attributed(
        self, providers: ProviderFactory
    ) -> None:
        response = httpx2.Response(401, request=httpx2.Request("POST", "https://x"))
        providers.failures.append(openai.APIStatusError("nope", response=response, body=None))
        with pytest.raises(AuthenticationError) as exc_info:
            await define()(google_api_key="k").evaluate(**INPUT)
        assert exc_info.value.dependency == "google"
        assert exc_info.value.model == "gemini-3-flash-preview"

    async def test_output_failures_are_resampled_up_to_max_retries(
        self, providers: ProviderFactory
    ) -> None:
        providers.failures.extend(
            [LLMOutputProcessingError("bad"), LLMOutputProcessingError("bad")]
        )
        evaluation = await define()(google_api_key="k", max_retries=2).evaluate(**INPUT)
        assert evaluation.result.verdict == "clear"
        assert len(providers.last.calls) == 3

    async def test_output_failures_surface_once_the_budget_is_spent(
        self, providers: ProviderFactory
    ) -> None:
        providers.failures.append(LLMOutputProcessingError("bad"))
        with pytest.raises(LLMOutputProcessingError):
            await define()(google_api_key="k", max_retries=0).evaluate(**INPUT)

    async def test_logs_never_carry_the_input_text(
        self, providers: ProviderFactory, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.INFO, logger="learning_commons_evaluators"):
            await define()(google_api_key="k").evaluate(**INPUT)
        assert caplog.records
        for record in caplog.records:
            assert INPUT["text"] not in record.getMessage()
            assert INPUT["text"] not in str(vars(record))

    async def test_a_failure_is_logged_with_the_error_class(
        self, providers: ProviderFactory, caplog: pytest.LogCaptureFixture
    ) -> None:
        with (
            caplog.at_level(logging.ERROR, logger="learning_commons_evaluators"),
            pytest.raises(InputValidationError),
        ):
            await define()(google_api_key="k").evaluate(text="t")
        [record] = [r for r in caplog.records if r.levelno == logging.ERROR]
        assert record.error == "InputValidationError"  # type: ignore[attr-defined]
        assert record.evaluator == "demo.area.thing"  # type: ignore[attr-defined]


def test_the_loop_guard_is_the_only_sync_restriction() -> None:
    # Sanity: outside a loop asyncio.run is available to evaluate_sync.
    asyncio.run(asyncio.sleep(0))


# --- attachments ----------------------------------------------------------------------

X_IMAGE: dict[str, Any] = {
    "formats": ["image/png", "image/jpeg", "image/webp"],
    "detect": "signature",
    "min_bytes": 64,
    "max_bytes": 5242880,
    "min_edge": 16,
    "max_edge": 2560,
}

IMAGE_INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["figures", "text"],
    "additionalProperties": False,
    "properties": {
        "figures": {
            "type": "array",
            "minItems": 1,
            "maxItems": 3,
            "items": {"type": "string", "minLength": 1, "x-image": X_IMAGE},
        },
        "text": {"type": "string", "minLength": 1},
    },
}

ATTACH_FIGURES = [{"input": "figures", "kind": "image", "position": "before_text"}]


def image_contract(
    input_schema: dict[str, Any] | None = None, attachments: Any = ATTACH_FIGURES
) -> Contract:
    """One step that attaches ``figures`` and renders only ``text``."""
    step = contract().model_dump(by_alias=True)["steps"][0]
    step["prompt"]["placeholders"] = {"text": {"required": True, "source": "input"}}
    step["attachments"] = attachments
    return contract(
        input_schema=copy.deepcopy(input_schema or IMAGE_INPUT_SCHEMA),
        preprocessing=[],
        steps=[step],
        documents={"system.txt": "system", "user.txt": "user: {text}"},
    )


class FiguresInput(BaseModel):
    figures: list[str]
    text: str


def define_images(**kwargs: Any) -> type[SingleStepEvaluator[FiguresInput, ThingOutput]]:
    class FiguresEvaluator(SingleStepEvaluator[FiguresInput, ThingOutput]):
        contract = image_contract(**kwargs)
        input_model = FiguresInput
        output_model = ThingOutput

    return FiguresEvaluator


def png(path: Path, width: int, height: int) -> bytes:
    """A real PNG of ``width``×``height`` written to ``path``; sizes differ, so order shows."""
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), (10, 120, 200)).save(buffer, "PNG")
    path.write_bytes(buffer.getvalue())
    return buffer.getvalue()


class TestAttachmentsOfRefusesADeclarationItCannotHonour:
    def declare(self, schema: dict[str, Any], attachments: Any = ATTACH_FIGURES) -> Any:
        step = image_contract(schema, attachments).steps[0]
        return attachments_of(step, schema, "Thing Evaluator")

    def schema(self, **figures: Any) -> dict[str, Any]:
        """The image schema with ``figures`` patched; a ``None`` value removes the key."""
        schema = copy.deepcopy(IMAGE_INPUT_SCHEMA)
        spec = schema["properties"]["figures"]
        for key, value in figures.items():
            if value is None:
                spec.pop(key, None)
            else:
                spec[key] = value
        return schema

    def bounds(self, **x_image: Any) -> dict[str, Any]:
        declared = {**X_IMAGE, **x_image}
        return self.schema(items={"type": "string", "x-image": declared})

    def test_accepts_a_complete_declaration(self) -> None:
        [attached] = self.declare(IMAGE_INPUT_SCHEMA)
        assert attached.input == "figures"
        assert attached.bounds == ImageBounds(
            formats=("image/png", "image/jpeg", "image/webp"),
            detect="signature",
            min_bytes=64,
            max_bytes=5242880,
            min_edge=16,
            max_edge=2560,
        )

    def test_a_step_with_no_attachments_declares_none(self) -> None:
        assert self.declare(IMAGE_INPUT_SCHEMA, attachments=[]) == ()

    def test_refuses_a_kind_other_than_image(self) -> None:
        with pytest.raises(
            ValueError, match='attaches "figures": kind "document" is not supported'
        ):
            self.declare(
                IMAGE_INPUT_SCHEMA,
                [{"input": "figures", "kind": "document", "position": "before_text"}],
            )

    @pytest.mark.parametrize("position", ["before_text", "after_text"])
    def test_reads_where_the_files_go(self, position: str) -> None:
        [attached] = self.declare(
            IMAGE_INPUT_SCHEMA, [{"input": "figures", "kind": "image", "position": position}]
        )
        assert attached.position == position

    def test_refuses_a_position_it_cannot_place(self) -> None:
        with pytest.raises(
            ValueError,
            match='attaches "figures": position "inline" is not supported; '
            "expected before_text or after_text",
        ):
            self.declare(
                IMAGE_INPUT_SCHEMA,
                [{"input": "figures", "kind": "image", "position": "inline"}],
            )

    def test_refuses_an_attached_input_the_schema_does_not_declare(self) -> None:
        with pytest.raises(ValueError, match='attaches "image": it must be an array input'):
            self.declare(
                IMAGE_INPUT_SCHEMA, [{"input": "image", "kind": "image", "position": "before_text"}]
            )

    def test_refuses_an_attached_input_that_could_be_omitted(self) -> None:
        with pytest.raises(ValueError, match="must be an array input"):
            self.declare(self.schema(type="string"))
        optional = copy.deepcopy(IMAGE_INPUT_SCHEMA)
        optional["required"] = ["text"]
        with pytest.raises(ValueError, match="must be listed in `required`"):
            self.declare(optional)
        with pytest.raises(ValueError, match="`minItems` of at least 1"):
            self.declare(self.schema(minItems=0))
        with pytest.raises(ValueError, match="`minItems` of at least 1"):
            self.declare(self.schema(minItems=None))

    def test_refuses_an_unbounded_or_inverted_item_count(self) -> None:
        with pytest.raises(ValueError, match="`maxItems` of at least `minItems`"):
            self.declare(self.schema(maxItems=None))
        with pytest.raises(ValueError, match="`maxItems` of at least `minItems`"):
            self.declare(self.schema(minItems=2, maxItems=1))

    def test_refuses_items_that_are_not_file_paths(self) -> None:
        with pytest.raises(ValueError, match="its items must be strings"):
            self.declare(self.schema(items={"type": "number", "x-image": X_IMAGE}))

    def test_refuses_items_with_no_x_image_block(self) -> None:
        with pytest.raises(ValueError, match="need an `x-image` block"):
            self.declare(self.schema(items={"type": "string"}))

    def test_refuses_a_missing_or_misspelled_bound_which_would_otherwise_pass_silently(
        self,
    ) -> None:
        missing = {k: v for k, v in X_IMAGE.items() if k != "min_edge"}
        with pytest.raises(ValueError, match="`x-image.min_edge` must be a number"):
            self.declare(self.schema(items={"type": "string", "x-image": missing}))
        with pytest.raises(ValueError, match="`x-image.max_bytes` must be a number"):
            self.declare(self.bounds(max_bytes=True))
        with pytest.raises(ValueError, match='`x-image.detect` must be "signature"'):
            self.declare(self.bounds(detect="extension"))

    def test_refuses_an_unsupported_or_empty_format_list(self) -> None:
        for formats in (["png"], [], ["image/png", "image/gif"], "image/png"):
            with pytest.raises(ValueError, match="`x-image.formats` must be a non-empty list"):
                self.declare(self.bounds(formats=formats))

    def test_refuses_inverted_bounds(self) -> None:
        with pytest.raises(ValueError, match="min_edge` exceeds `max_edge"):
            self.declare(self.bounds(min_edge=3000))
        with pytest.raises(ValueError, match="min_bytes` exceeds `max_bytes"):
            self.declare(self.bounds(min_bytes=9_000_000_000))

    def test_fails_when_the_class_is_created_not_when_it_is_first_called(self) -> None:
        with pytest.raises(ValueError, match="need an `x-image` block"):
            define_images(input_schema=self.schema(items={"type": "string"}))


class TestAttachesImages:
    async def test_loads_every_path_in_order_and_keeps_them_out_of_the_prompt(
        self, providers: ProviderFactory, tmp_path: Path
    ) -> None:
        a = png(tmp_path / "a.png", 100, 50)
        b = png(tmp_path / "b.png", 60, 90)
        c = png(tmp_path / "c.png", 30, 30)
        paths = [str(tmp_path / name) for name in ("a.png", "b.png", "c.png")]

        await define_images()(google_api_key="k").evaluate(figures=paths, text="Three figures.")

        [call] = providers.calls
        assert [part.data for part in call["attachments"]] == [a, b, c]
        assert {part.media_type for part in call["attachments"]} == {"image/png"}
        assert call["messages"][1]["content"] == "user: Three figures."
        for message in call["messages"]:
            assert str(tmp_path) not in message["content"]

    @pytest.mark.parametrize("position", ["before_text", "after_text"])
    async def test_hands_the_provider_each_image_with_the_position_the_contract_declares(
        self, providers: ProviderFactory, tmp_path: Path, position: str
    ) -> None:
        png(tmp_path / "a.png", 100, 50)
        png(tmp_path / "b.png", 60, 90)
        evaluator = define_images(
            attachments=[{"input": "figures", "kind": "image", "position": position}]
        )(google_api_key="k")
        await evaluator.evaluate(
            figures=[str(tmp_path / "a.png"), str(tmp_path / "b.png")], text="Two."
        )
        assert [part.position for part in providers.calls[0]["attachments"]] == [position] * 2

    async def test_accepts_the_input_model(
        self, providers: ProviderFactory, tmp_path: Path
    ) -> None:
        data = png(tmp_path / "a.png", 100, 50)
        evaluator = define_images()(google_api_key="k")
        await evaluator.evaluate(FiguresInput(figures=[str(tmp_path / "a.png")], text="One."))
        assert [part.data for part in providers.calls[0]["attachments"]] == [data]

    async def test_reads_the_images_once_however_many_times_the_output_is_resampled(
        self, providers: ProviderFactory, tmp_path: Path
    ) -> None:
        png(tmp_path / "a.png", 100, 50)
        providers.failures.extend(
            [LLMOutputProcessingError("bad"), LLMOutputProcessingError("bad")]
        )
        reads: list[str] = []
        real = image_source.load_image

        def counting(field: str, path: str, bounds: ImageBounds, **kwargs: Any) -> Any:
            reads.append(field)
            return real(field, path, bounds, **kwargs)

        with patch("learning_commons_evaluators.evaluators.single_step.load_image", counting):
            await define_images()(google_api_key="k", max_retries=2).evaluate(
                figures=[str(tmp_path / "a.png")], text="One."
            )
        assert reads == ["figures[0]"]
        assert len(providers.calls) == 3
        assert all(len(call["attachments"]) == 1 for call in providers.calls)

    async def test_an_unreadable_image_fails_validation_before_any_call(
        self, providers: ProviderFactory, tmp_path: Path
    ) -> None:
        with pytest.raises(InputValidationError, match=r"^figures\[0\]: could not read file"):
            await define_images()(google_api_key="k").evaluate(
                figures=[str(tmp_path / "missing.png")], text="One."
            )
        assert providers.calls == []

    async def test_an_image_outside_its_bounds_fails_before_any_call(
        self, providers: ProviderFactory, tmp_path: Path
    ) -> None:
        png(tmp_path / "ok.png", 100, 50)
        png(tmp_path / "narrow.png", 10, 400)
        with pytest.raises(InputValidationError, match=r"^figures\[1\]: .*10×400 px"):
            await define_images()(google_api_key="k").evaluate(
                figures=[str(tmp_path / "ok.png"), str(tmp_path / "narrow.png")], text="Two."
            )
        assert providers.calls == []

    def test_refuses_a_provider_that_does_not_declare_attachment_support(self) -> None:
        def text_only(config: ProviderConfig) -> FakeProvider:
            return FakeProvider(config, _verdict, supports_attachments=False)

        with (
            patch("learning_commons_evaluators.evaluators.base.create_provider", text_only),
            pytest.raises(
                ConfigurationError,
                match="Thing attaches images to each request, and the configured provider "
                '"google:gemini-3-flash-preview" does not declare support for attachments',
            ),
        ):
            define_images()(google_api_key="k")

    async def test_a_text_only_provider_still_runs_a_contract_that_attaches_nothing(self) -> None:
        @dataclass
        class TextOnly:
            """Implements the protocol as it stood before attachments: no flag, no parameter."""

            config: ProviderConfig

            @property
            def label(self) -> str:
                return "google:text-only"

            async def generate_structured(
                self,
                messages: Any,
                schema: type[BaseModel],
                *,
                temperature: float | None = None,
                max_tokens: int | None = None,
            ) -> LLMResponse[Any]:
                return LLMResponse(
                    data=_verdict(schema), model="m", usage=TokenUsage(1, 1), latency_ms=1
                )

            async def generate_text(self, *args: Any, **kwargs: Any) -> Any:  # pragma: no cover
                raise AssertionError("not called")

        with patch("learning_commons_evaluators.evaluators.base.create_provider", TextOnly):
            evaluation = await define()(google_api_key="k").evaluate(**INPUT)
        assert evaluation.result.verdict == "clear"


# --- x-model-only output fields ------------------------------------------------------


class ThingResponse(BaseModel):
    verdict: str
    reasoning: str
    working: str


def model_only_contract() -> Contract:
    """``working`` is asked of the model and kept from the caller."""
    schema = contract().output_schema
    schema["required"].append("working")
    schema["properties"]["working"] = {"type": "string", "x-model-only": True}
    return contract(output_schema=schema)


def _with_working(schema: type[BaseModel]) -> BaseModel:
    return schema.model_validate({"verdict": "clear", "reasoning": "because", "working": "w"})


class TestModelOnlyFields:
    @pytest.fixture
    def providers(self) -> Any:
        factory = ProviderFactory(payload=_with_working)
        with patch("learning_commons_evaluators.evaluators.base.create_provider", factory):
            yield factory

    def define(
        self,
        response: type[BaseModel] | None = ThingResponse,
        output: type[BaseModel] = ThingOutput,
        declared: Contract | None = None,
    ) -> type[SingleStepEvaluator[ThingInput, Any]]:
        class ThingEvaluator(SingleStepEvaluator[ThingInput, Any]):
            contract = declared or model_only_contract()
            input_model = ThingInput
            output_model = output
            response_model = response

        return ThingEvaluator

    async def test_asks_the_model_for_them_and_returns_without_them(
        self, providers: ProviderFactory
    ) -> None:
        evaluator = self.define()(google_api_key="k")
        result = await evaluator.evaluate(**INPUT)
        assert providers.calls[0]["schema"] is ThingResponse
        assert isinstance(result.result, ThingOutput)
        assert result.result.model_dump() == {"verdict": "clear", "reasoning": "because"}
        assert read_outcome(result, evaluator.metadata.outcome).score == "clear"

    async def test_matches_the_fields_by_wire_name_not_attribute_name(
        self, providers: ProviderFactory
    ) -> None:
        # Both pass the class check, which compares wire names, so the copy must use them too.
        class AliasedResponse(BaseModel):
            response_verdict: str = Field(alias="verdict")
            reasoning: str
            working: str

        class AliasedOutput(BaseModel):
            output_verdict: str = Field(alias="verdict")
            reasoning: str

        evaluator = self.define(response=AliasedResponse, output=AliasedOutput)(google_api_key="k")
        result = await evaluator.evaluate(**INPUT)
        assert isinstance(result.result, AliasedOutput)
        assert result.result.model_dump(by_alias=True) == {
            "verdict": "clear",
            "reasoning": "because",
        }

    def test_refuses_a_class_that_would_return_them(self) -> None:
        with pytest.raises(
            ValueError, match="marks working x-model-only; declare a response_model"
        ):
            self.define(response=None)
        with pytest.raises(ValueError, match="output_model ThingResponse must hold exactly"):
            self.define(output=ThingResponse)

    def test_refuses_a_response_model_that_does_not_ask_for_every_property(self) -> None:
        with pytest.raises(ValueError, match="response_model ThingOutput must hold every"):
            self.define(response=ThingOutput)

    def test_refuses_a_response_model_when_nothing_is_marked(self) -> None:
        with pytest.raises(ValueError, match="marks no property x-model-only"):
            self.define(declared=contract())


# --- the prepare-inputs hook ----------------------------------------------------------


class TestPrepareInputs:
    def define(self, prepare: Any) -> type[SingleStepEvaluator[ThingInput, ThingOutput]]:
        class ThingEvaluator(SingleStepEvaluator[ThingInput, ThingOutput]):
            contract = globals()["contract"]()
            input_model = ThingInput
            output_model = ThingOutput

            def _prepare_inputs(self, values: dict[str, Any]) -> dict[str, Any]:
                return dict(prepare(values))

        return ThingEvaluator

    async def test_sees_validated_inputs_and_what_it_returns_is_rendered(
        self, providers: ProviderFactory
    ) -> None:
        seen: list[dict[str, Any]] = []

        def shout(values: dict[str, Any]) -> dict[str, Any]:
            seen.append(values)
            return {**values, "text": values["text"].upper()}

        await self.define(shout)(google_api_key="k").evaluate(text=INPUT["text"], grade_level=4)
        # Validated first: the int grade is already its token.
        assert seen == [{"text": INPUT["text"], "grade_level": "4"}]
        assert providers.calls[0]["messages"][1]["content"].startswith(
            f"user: {INPUT['text'].upper()} at 4"
        )

    async def test_a_rejection_is_raised_before_any_call_and_logged(
        self, providers: ProviderFactory, caplog: pytest.LogCaptureFixture
    ) -> None:
        def refuse(values: dict[str, Any]) -> dict[str, Any]:
            raise InputValidationError("not like that")

        with pytest.raises(InputValidationError, match="not like that"):
            await self.define(refuse)(google_api_key="k").evaluate(**INPUT)
        assert providers.calls == []
        assert "Thing evaluation failed" in caplog.text
