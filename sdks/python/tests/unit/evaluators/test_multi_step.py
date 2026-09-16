"""The multi-step flow, tested on synthetic contracts so every branch is reachable."""

from __future__ import annotations

import json
import logging
from typing import Any
from unittest.mock import patch

import httpx2
import openai
import pytest
import textstat
from pydantic import BaseModel

from learning_commons_evaluators import (
    AuthenticationError,
    ConfigurationError,
    DependencyError,
    EvaluationResult,
    InputValidationError,
    LLMOutputProcessingError,
    ModelOverride,
    Provider,
    read_outcome,
)
from learning_commons_evaluators.contracts.loader import Contract
from learning_commons_evaluators.evaluators.multi_step import MultiStepEvaluator, as_prompt_text
from tests.unit.conftest import ProviderFactory

STABLE_ID = "22222222-2222-2222-2222-222222222222"


def contract(**overrides: Any) -> Contract:
    """A two-step contract: prose, then a rating that reads it and the loaded rubric."""
    raw: dict[str, Any] = {
        "evaluator": {
            "id": "demo.area.chain",
            "stable_id": STABLE_ID,
            "id_history": ["demo.area.old_chain"],
            "name": "Chain Evaluator",
            "description": "Demonstration multi-step contract.",
            "supported_grades": ["3", "4", "5"],
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
            },
            {
                "id": "rubric_low",
                "type": "computation",
                "kind": "load_rubric_text",
                "input": "grade_level",
                "output": "rubric",
                "source_path": "rubric-low.txt",
                "condition": {"input": "grade_level", "in": ["3"]},
                "implementation": {"python": {"library": "pathlib", "function": "load_low"}},
            },
            {
                "id": "rubric_high",
                "type": "computation",
                "kind": "load_rubric_text",
                "input": "grade_level",
                "output": "rubric",
                "source_path": "rubric-high.txt",
                "condition": {"input": "grade_level", "in": ["4", "5"]},
                "implementation": {"python": {"library": "pathlib", "function": "load_high"}},
            },
            {
                "id": "shouted",
                "type": "computation",
                "kind": "custom",
                "input": "steps.notes.output",
                "output": "shouted",
                "implementation": {"python": {"library": "custom", "function": "shout"}},
            },
        ],
        "steps": [
            {
                "id": "notes",
                "type": "llm",
                "prompt": {
                    "messages": [{"role": "user", "source_path": "notes-user.txt"}],
                    "placeholders": {"text": {"required": True, "source": "input"}},
                },
                "model": {"provider": "openai", "name": "gpt-4o-2024-11-20"},
                "generation": {"temperature": 0},
                "parser": {"kind": "structured_output"},
            },
            {
                "id": "rate",
                "type": "llm",
                "prompt": {
                    "messages": [
                        {"role": "system", "source_path": "rate-system.txt"},
                        {"role": "user", "source_path": "rate-user.txt"},
                    ],
                    "placeholders": {
                        "grade_level": {"required": True, "source": "input"},
                        "excerpt": {"required": True, "source": "input.text"},
                        "fk_score": {"required": True, "source": "preprocessing.fk_score"},
                        "rubric": {"required": True, "source": "preprocessing.rubric"},
                        "notes": {"required": True, "source": "steps.notes.output"},
                        "shouted": {"required": True, "source": "preprocessing.shouted"},
                    },
                },
                "model": {"provider": "google", "name": "gemini-2.5-pro"},
                "generation": {"temperature": 0.5},
                "parser": {"kind": "structured_output"},
            },
        ],
        "outcome": {"score": "verdict", "reasoning": "reasoning"},
        "documents": {
            "notes-user.txt": "notes: {text}",
            "rate-system.txt": "system: {rubric}",
            "rate-user.txt": "rate: {excerpt} at {grade_level} fk {fk_score} notes {notes} / {shouted}",
            "rubric-low.txt": "LOW RUBRIC",
            "rubric-high.txt": "HIGH RUBRIC",
        },
    }
    raw.update(overrides)
    return Contract.model_validate(raw)


class ChainOutput(BaseModel):
    verdict: str
    reasoning: str


class Notes(BaseModel):
    """A step output that is not the evaluator's result."""

    notes: str


class ChainInput(BaseModel):
    text: str
    grade_level: int


def shout(notes: Any) -> str:
    return str(notes).upper()


def define(**overrides: Any) -> type[MultiStepEvaluator[ChainInput, ChainOutput]]:
    steps: dict[str, Any] = overrides.pop("step_models", {"notes": None, "rate": ChainOutput})
    functions: dict[str, Any] = overrides.pop("computations", {"shout": shout})

    class ChainEvaluator(MultiStepEvaluator[ChainInput, ChainOutput]):
        contract = globals()["contract"](**overrides)
        input_model = ChainInput
        output_model = ChainOutput
        step_models = steps
        computations = functions

    return ChainEvaluator


INPUT = {"text": "The cat sat on the mat.", "grade_level": "3"}
FK = textstat.flesch_kincaid_grade(INPUT["text"])
FK_TEXT = str(round(FK, 2)) if not round(FK, 2).is_integer() else str(int(round(FK, 2)))
KEYS = {"openai_api_key": "o", "google_api_key": "g"}


def _verdict(schema: type[BaseModel]) -> BaseModel:
    return schema.model_validate({"verdict": "clear", "reasoning": "because"})


@pytest.fixture
def providers() -> Any:
    factory = ProviderFactory(payload=_verdict, prose="  the notes  ")
    with patch("learning_commons_evaluators.evaluators.base.create_provider", factory):
        yield factory


class TestRefusesAContractItCannotRun:
    def test_refuses_a_single_step_contract(self) -> None:
        raw = contract().model_dump(by_alias=True)
        with pytest.raises(
            ValueError, match=r"declares 1 step\(s\); MultiStepEvaluator runs more than one"
        ):
            define(steps=raw["steps"][:1], step_models={"notes": ChainOutput})

    def test_refuses_a_step_with_no_step_models_entry(self) -> None:
        with pytest.raises(ValueError, match='Step "rate".*has no step_models entry'):
            define(step_models={"notes": None})

    def test_refuses_a_step_models_entry_the_contract_does_not_declare(self) -> None:
        with pytest.raises(ValueError, match='step_models names "ghost"'):
            define(step_models={"notes": None, "rate": ChainOutput, "ghost": ChainOutput})

    def test_refuses_a_last_step_that_does_not_produce_the_output_model(self) -> None:
        with pytest.raises(
            ValueError, match=r'Step "rate" of Chain Evaluator config.json can end a run'
        ):
            define(step_models={"notes": ChainOutput, "rate": None})

    def test_refuses_a_conditional_branch_ending_on_a_non_output_step(self) -> None:
        # Shaped like Vocabulary Complexity: an unconditional first step, then one
        # conditional step per grade band. Checking only the last declared step misses the
        # grade-3 branch, which ends on notes_grade_3 and produces Notes.
        raw = contract().model_dump(by_alias=True)
        raw["steps"] = [
            raw["steps"][0],
            {
                **contract().model_dump(by_alias=True)["steps"][0],
                "id": "notes_grade_3",
                "condition": {"input": "grade_level", "in": ["3"]},
            },
            {**raw["steps"][1], "condition": {"input": "grade_level", "in": ["4", "5"]}},
        ]
        with pytest.raises(ValueError, match='Step "notes_grade_3".*can end a run'):
            define(
                steps=raw["steps"],
                step_models={"notes": None, "notes_grade_3": Notes, "rate": ChainOutput},
            )

    def test_accepts_a_branching_contract_whose_every_terminal_step_produces_the_output(
        self,
    ) -> None:
        # Vocabulary Complexity's shape, which the simpler rule "every step from the last
        # unconditional one onward" would wrongly reject: its last unconditional step is
        # the prose one, and two conditional steps follow it.
        raw = contract().model_dump(by_alias=True)
        raw["steps"] = [
            raw["steps"][0],
            {
                **raw["steps"][1],
                "id": "rate_low",
                "condition": {"input": "grade_level", "in": ["3"]},
            },
            {**raw["steps"][1], "condition": {"input": "grade_level", "in": ["4", "5"]}},
        ]
        evaluator = define(
            steps=raw["steps"],
            step_models={"notes": None, "rate_low": ChainOutput, "rate": ChainOutput},
        )
        assert evaluator.metadata.id == "demo.area.chain"

    def test_refuses_an_optional_step(self) -> None:
        raw = contract().model_dump(by_alias=True)
        raw["steps"][0]["optional"] = True
        with pytest.raises(ValueError, match='Step "notes".*is optional'):
            define(steps=raw["steps"])

    def test_refuses_a_placeholder_source_it_cannot_read(self) -> None:
        raw = contract().model_dump(by_alias=True)
        raw["steps"][1]["prompt"]["placeholders"]["notes"]["source"] = "elsewhere.notes"
        with pytest.raises(ValueError, match='declares an unsupported source "elsewhere.notes"'):
            define(steps=raw["steps"])

    def test_refuses_a_placeholder_reading_a_step_the_contract_does_not_declare(self) -> None:
        raw = contract().model_dump(by_alias=True)
        raw["steps"][1]["prompt"]["placeholders"]["notes"]["source"] = "steps.ghost.output"
        with pytest.raises(ValueError, match='reads step "ghost", which it does not declare'):
            define(steps=raw["steps"])

    def test_refuses_a_custom_entry_whose_function_is_not_supplied(self) -> None:
        with pytest.raises(
            ValueError, match=r'custom function "shout", which this evaluator does not supply'
        ):
            define(computations={})

    def test_refuses_a_rubric_entry_whose_document_was_not_bundled(self) -> None:
        raw = contract().model_dump(by_alias=True)
        del raw["documents"]["rubric-low.txt"]
        with pytest.raises(LookupError, match='names "rubric-low.txt", which was not bundled'):
            define(documents=raw["documents"])

    def test_refuses_a_rubric_entry_with_no_source_path(self) -> None:
        raw = contract().model_dump(by_alias=True)
        raw["preprocessing"][1]["source_path"] = None
        with pytest.raises(ValueError, match='"rubric_low".*names no source_path'):
            define(preprocessing=raw["preprocessing"])

    def test_refuses_a_duplicated_step_id(self) -> None:
        # Two steps under one id would alias: the second's output overwrites the first's,
        # and one step_models entry would satisfy the completeness check for both. The
        # registry schema does not require step ids to be unique, so this is the only check.
        raw = contract().model_dump(by_alias=True)
        raw["steps"].append({**raw["steps"][0]})
        with pytest.raises(ValueError, match='Step "notes" is declared twice'):
            define(steps=raw["steps"])

    def test_refuses_an_api_preprocessing_entry(self) -> None:
        # As the single-step base does. An api entry has an endpoint, auth and pagination
        # to honour; running it as a local computation would quietly do something else.
        raw = contract().model_dump(by_alias=True)
        raw["preprocessing"][0]["type"] = "api"
        with pytest.raises(ValueError, match='"fk_score".*is an "api" entry'):
            define(preprocessing=raw["preprocessing"])

    def test_refuses_an_entry_reading_an_input_the_schema_does_not_declare(self) -> None:
        # Resolved from the validated inputs at evaluation, where an undeclared name reads
        # as "" and the computation returns a plausible number for it.
        raw = contract().model_dump(by_alias=True)
        raw["preprocessing"][0]["input"] = "txet"
        with pytest.raises(ValueError, match='"fk_score".*reads input "txet"'):
            define(preprocessing=raw["preprocessing"])

    def test_refuses_an_entry_reading_a_step_the_contract_does_not_declare(self) -> None:
        raw = contract().model_dump(by_alias=True)
        raw["preprocessing"][3]["input"] = "steps.ghost.output"
        with pytest.raises(ValueError, match='"shouted".*reads step "ghost"'):
            define(preprocessing=raw["preprocessing"])

    def test_refuses_a_computation_entry_with_no_input(self) -> None:
        raw = contract().model_dump(by_alias=True)
        raw["preprocessing"][0]["input"] = None
        with pytest.raises(ValueError, match='"fk_score".*names no input to compute from'):
            define(preprocessing=raw["preprocessing"])

    def test_a_rubric_entry_is_not_input_checked_because_it_reads_none(self) -> None:
        # Its value is the document; the contract names an input for documentation, and
        # `condition` is what selects between entries.
        raw = contract().model_dump(by_alias=True)
        raw["preprocessing"][1]["input"] = "grade_level_typo"
        assert define(preprocessing=raw["preprocessing"]).metadata.id == "demo.area.chain"

    def test_refuses_an_entry_that_names_no_output(self) -> None:
        raw = contract().model_dump(by_alias=True)
        raw["preprocessing"][0]["output"] = None
        with pytest.raises(ValueError, match='"fk_score".*names no output'):
            define(preprocessing=raw["preprocessing"])

    @pytest.mark.parametrize(
        ("patch_entry", "message"),
        [
            ({"library": "nltk"}, 'Unsupported preprocessing library "nltk"'),
            ({"function": "nope"}, 'Function "nope" not found in textstat'),
            ({"post_transform": {"type": "floor"}}, 'Unsupported post_transform type "floor"'),
        ],
        ids=["library", "function", "transform"],
    )
    def test_refuses_a_library_computation_this_sdk_cannot_run(
        self, patch_entry: dict[str, Any], message: str
    ) -> None:
        # Our gap, not the provider's: it must never reach evaluate(), where the error
        # boundary would attribute it to the model's vendor as an LLMProviderError.
        raw = contract().model_dump(by_alias=True)
        raw["preprocessing"][0]["implementation"]["python"].update(patch_entry)
        with pytest.raises(
            NotImplementedError, match=f'Preprocessing "fk_score" in Chain Evaluator.*{message}'
        ):
            define(preprocessing=raw["preprocessing"])


class TestReadsBehaviourFromTheContract:
    def test_metadata_reports_every_provider_the_steps_use(self) -> None:
        metadata = define().metadata
        assert metadata.id == "demo.area.chain"
        assert metadata.stable_id == STABLE_ID
        assert metadata.id_history == ("demo.area.old_chain",)
        assert metadata.default_providers == (Provider.OPENAI, Provider.GOOGLE)
        assert metadata.label == "Chain"

    def test_builds_one_provider_per_distinct_model(self, providers: ProviderFactory) -> None:
        define()(**KEYS)
        assert [(p.config.type, p.config.model, p.config.api_key) for p in providers.created] == [
            (Provider.OPENAI, "gpt-4o-2024-11-20", "o"),
            (Provider.GOOGLE, "gemini-2.5-pro", "g"),
        ]

    def test_an_override_collapses_every_step_onto_one_client(
        self, providers: ProviderFactory
    ) -> None:
        # The steps declare two vendors and two models, but an override sends them all to
        # one, so keying on the declared models would build identical clients per step.
        override = ModelOverride(provider=Provider.ANTHROPIC, model="claude-opus-5")
        define()(anthropic_api_key="a", model_override=override)
        assert [(p.config.type, p.config.model) for p in providers.created] == [
            (Provider.ANTHROPIC, "claude-opus-5")
        ]

    def test_steps_sharing_a_model_share_one_client(self, providers: ProviderFactory) -> None:
        raw = contract().model_dump(by_alias=True)
        raw["steps"][1]["model"] = raw["steps"][0]["model"]
        define(steps=raw["steps"])(**KEYS)
        assert len(providers.created) == 1

    async def test_runs_the_steps_in_order_with_their_own_schema_and_temperature(
        self, providers: ProviderFactory
    ) -> None:
        await define()(**KEYS).evaluate(**INPUT)
        assert [(c["schema"], c["temperature"]) for c in providers.calls] == [
            (None, 0),
            (ChainOutput, 0.5),
        ]

    async def test_resolves_every_source_a_placeholder_can_name(
        self, providers: ProviderFactory
    ) -> None:
        await define()(**KEYS).evaluate(**INPUT)
        notes, rate = providers.calls
        assert notes["messages"] == [{"role": "user", "content": "notes: The cat sat on the mat."}]
        assert rate["messages"] == [
            # The rubric for grade 3, chosen by the entry's condition.
            {"role": "system", "content": "system: LOW RUBRIC"},
            {
                "role": "user",
                # The prose step's answer is trimmed, and the custom computation read it.
                "content": (
                    f"rate: The cat sat on the mat. at 3 fk {FK_TEXT} notes the notes / THE NOTES"
                ),
            },
        ]

    @pytest.mark.parametrize(("grade", "rubric"), [(3, "LOW RUBRIC"), (4, "HIGH RUBRIC")])
    async def test_a_conditional_entry_supplies_the_value_for_its_own_inputs(
        self, providers: ProviderFactory, grade: int, rubric: str
    ) -> None:
        await define()(**KEYS).evaluate(text=INPUT["text"], grade_level=grade)
        assert providers.calls[1]["messages"][0]["content"] == f"system: {rubric}"

    async def test_a_conditional_step_only_runs_for_its_own_inputs(
        self, providers: ProviderFactory
    ) -> None:
        raw = contract().model_dump(by_alias=True)
        raw["steps"][1]["condition"] = {"input": "grade_level", "in": ["3"]}
        evaluator = define(steps=raw["steps"])
        await evaluator(**KEYS).evaluate(text=INPUT["text"], grade_level=3)
        assert [c["schema"] for c in providers.calls] == [None, ChainOutput]

    async def test_a_computation_is_run_once_however_many_placeholders_read_it(
        self, providers: ProviderFactory
    ) -> None:
        raw = contract().model_dump(by_alias=True)
        raw["steps"][1]["prompt"]["placeholders"]["again"] = {
            "required": True,
            "source": "preprocessing.shouted",
        }
        raw["documents"]["rate-user.txt"] += " {again}"
        calls: list[Any] = []

        def counted(notes: Any) -> str:
            calls.append(notes)
            return shout(notes)

        evaluator = define(
            steps=raw["steps"], documents=raw["documents"], computations={"shout": counted}
        )
        await evaluator(**KEYS).evaluate(**INPUT)
        assert len(calls) == 1
        assert providers.calls[1]["messages"][1]["content"].endswith("THE NOTES THE NOTES")


class TestEnvelope:
    async def test_names_every_model_that_ran_and_sums_their_tokens(
        self, providers: ProviderFactory
    ) -> None:
        evaluation = await define()(**KEYS).evaluate(**INPUT)
        assert isinstance(evaluation, EvaluationResult)
        assert evaluation.evaluator == "demo.area.chain"
        assert evaluation.result == ChainOutput(verdict="clear", reasoning="because")
        assert evaluation.metadata.model == "openai:gpt-4o-2024-11-20+google:gemini-2.5-pro"
        # 5 + 7 in, 2 + 3 out: the prose step and the rating step, added.
        assert evaluation.metadata.token_usage.input_tokens == 12
        assert evaluation.metadata.token_usage.output_tokens == 5

    async def test_steps_on_one_model_name_it_once(self, providers: ProviderFactory) -> None:
        raw = contract().model_dump(by_alias=True)
        raw["steps"][1]["model"] = raw["steps"][0]["model"]
        evaluation = await define(steps=raw["steps"])(**KEYS).evaluate(**INPUT)
        assert evaluation.metadata.model == "openai:gpt-4o-2024-11-20"

    async def test_an_override_collapses_the_label_to_the_one_model_in_use(
        self, providers: ProviderFactory
    ) -> None:
        override = ModelOverride(provider=Provider.ANTHROPIC, model="claude-opus-5")
        evaluator = define()(anthropic_api_key="a", model_override=override)
        evaluation = await evaluator.evaluate(**INPUT)
        assert evaluation.metadata.model == "anthropic:claude-opus-5"

    async def test_read_outcome_reads_the_final_steps_payload(
        self, providers: ProviderFactory
    ) -> None:
        evaluator = define()(**KEYS)
        outcome = read_outcome(await evaluator.evaluate(**INPUT), evaluator.metadata.outcome)
        assert (outcome.score, outcome.reasoning) == ("clear", "because")

    def test_evaluate_sync(self, providers: ProviderFactory) -> None:
        assert define()(**KEYS).evaluate_sync(**INPUT).result.verdict == "clear"

    async def test_accepts_the_input_model_with_an_int_grade(
        self, providers: ProviderFactory
    ) -> None:
        await define()(**KEYS).evaluate(ChainInput(text="Hello there.", grade_level=4))
        assert "at 4 fk" in providers.calls[1]["messages"][1]["content"]

    async def test_rejects_both_input_forms_at_once(self, providers: ProviderFactory) -> None:
        with pytest.raises(TypeError, match="not both"):
            await define()(**KEYS).evaluate(ChainInput(text="t", grade_level=3), text="t")


class TestFailures:
    async def test_validation_happens_before_any_call(self, providers: ProviderFactory) -> None:
        with pytest.raises(InputValidationError, match='Invalid grade_level "9"'):
            await define()(**KEYS).evaluate(text=INPUT["text"], grade_level=9)
        assert providers.calls == []

    async def test_a_failure_in_the_first_step_names_that_steps_vendor(
        self, providers: ProviderFactory
    ) -> None:
        # Attributed by ``call_with_resampling``, which knows the client it called; the
        # evaluate() boundary re-classifies nothing, so a provider failure arrives already
        # mapped and carrying the right vendor.
        response = httpx2.Response(401, request=httpx2.Request("POST", "https://x"))
        providers.failures.append(openai.APIStatusError("nope", response=response, body=None))
        with pytest.raises(AuthenticationError) as failure:
            await define()(**KEYS).evaluate(**INPUT)
        assert (failure.value.dependency, failure.value.model) == ("openai", "gpt-4o-2024-11-20")

    async def test_a_failure_in_a_later_step_names_that_steps_vendor(
        self, providers: ProviderFactory
    ) -> None:
        response = httpx2.Response(401, request=httpx2.Request("POST", "https://x"))
        evaluator = define()(**KEYS)
        # Only the rating step's client fails, which is the Google one.
        providers.created[1].failures = [
            openai.APIStatusError("nope", response=response, body=None)
        ]
        with pytest.raises(AuthenticationError) as failure:
            await evaluator.evaluate(**INPUT)
        assert (failure.value.dependency, failure.value.model) == ("google", "gemini-2.5-pro")

    async def test_output_failures_are_resampled_per_step(self, providers: ProviderFactory) -> None:
        providers.failures.append(LLMOutputProcessingError("bad"))
        evaluation = await define()(**KEYS, max_retries=1).evaluate(**INPUT)
        assert evaluation.result.verdict == "clear"
        assert [c["schema"] for c in providers.calls] == [None, None, ChainOutput]

    async def test_output_failures_surface_once_the_budget_is_spent(
        self, providers: ProviderFactory
    ) -> None:
        providers.failures.append(LLMOutputProcessingError("bad"))
        with pytest.raises(LLMOutputProcessingError):
            await define()(**KEYS, max_retries=0).evaluate(**INPUT)

    async def test_a_contract_whose_branches_all_miss_is_a_contract_fault(
        self, providers: ProviderFactory
    ) -> None:
        # Nothing ran, so nothing can be attributed: reporting a provider here would be a
        # factual error about which service failed (spec §6.2), not just the wrong class.
        # Both steps produce the output model, so the terminal-step rule accepts the
        # contract — with every step conditional, either of them could end a run.
        raw = contract().model_dump(by_alias=True)
        for step in raw["steps"]:
            step["condition"] = {"input": "grade_level", "in": ["5"]}
        evaluator = define(
            steps=raw["steps"], step_models={"notes": ChainOutput, "rate": ChainOutput}
        )(**KEYS)
        with pytest.raises(ConfigurationError, match="No step of Chain Evaluator runs") as failure:
            await evaluator.evaluate(**INPUT)
        assert not isinstance(failure.value, DependencyError)
        assert providers.calls == []

    async def test_a_required_placeholder_bound_to_an_optional_input_is_a_contract_fault(
        self, providers: ProviderFactory
    ) -> None:
        # The schema makes `note` optional; the placeholder makes it required. Only a run
        # that omits it can discover the disagreement, so unlike the refusals above this
        # one cannot move to class creation — it is a runtime contract fault whatever else
        # is checked there.
        raw = contract().model_dump(by_alias=True)
        raw["input_schema"]["properties"]["note"] = {"type": "string"}
        raw["steps"][0]["prompt"]["placeholders"]["note"] = {
            "required": True,
            "source": "input.note",
        }
        raw["documents"]["notes-user.txt"] = "notes: {text} {note}"
        evaluator = define(
            steps=raw["steps"], documents=raw["documents"], input_schema=raw["input_schema"]
        )(**KEYS)
        with pytest.raises(ConfigurationError, match='Placeholder "note".*has no value'):
            await evaluator.evaluate(**INPUT)

    async def test_a_branch_ending_on_a_prose_step_fails_rather_than_returning_it(
        self, providers: ProviderFactory
    ) -> None:
        # The rating step is skipped for grade 3, so the run ends on the prose step, whose
        # answer is not the evaluator's result.
        # Accepted at class creation: the trailing conditional step does produce the output
        # model, so the terminal-step rule is satisfied. Only a grade the condition excludes
        # reaches the end of the run on the prose step, which is why the runtime guard stays.
        raw = contract().model_dump(by_alias=True)
        raw["steps"][1]["condition"] = {"input": "grade_level", "in": ["5"]}
        evaluator = define(steps=raw["steps"])(**KEYS)
        with pytest.raises(ConfigurationError, match="ends on a step whose output is not"):
            await evaluator.evaluate(**INPUT)

    async def test_logs_never_carry_the_input_text(
        self, providers: ProviderFactory, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.DEBUG, logger="learning_commons_evaluators"):
            await define()(**KEYS).evaluate(**INPUT)
        assert caplog.records
        for record in caplog.records:
            assert INPUT["text"] not in record.getMessage()
            assert INPUT["text"] not in str(vars(record))

    async def test_a_failure_records_how_many_steps_completed(
        self, providers: ProviderFactory, caplog: pytest.LogCaptureFixture
    ) -> None:
        evaluator = define()(**KEYS, max_retries=0)
        providers.created[1].failures = [LLMOutputProcessingError("bad")]
        with (
            caplog.at_level(logging.ERROR, logger="learning_commons_evaluators"),
            pytest.raises(LLMOutputProcessingError),
        ):
            await evaluator.evaluate(**INPUT)
        [record] = [r for r in caplog.records if r.levelno == logging.ERROR]
        assert record.completed_steps == 1  # type: ignore[attr-defined]


class TestStepOutputText:
    def test_a_prose_answer_reaches_the_next_prompt_as_itself(self) -> None:
        assert as_prompt_text("plain") == "plain"

    def test_a_structured_answer_reaches_it_as_compact_json(self) -> None:
        rendered = as_prompt_text(ChainOutput(verdict="clear", reasoning="because"))
        # Compact, as JavaScript's JSON.stringify renders it, so both SDKs bind the same text.
        assert rendered == '{"verdict":"clear","reasoning":"because"}'
        assert json.loads(rendered) == {"verdict": "clear", "reasoning": "because"}

    def test_a_plain_mapping_reaches_it_as_compact_json(self) -> None:
        assert as_prompt_text({"a": 1, "b": [2, 3]}) == '{"a":1,"b":[2,3]}'

    def test_non_ascii_characters_reach_it_unescaped(self) -> None:
        # JSON.stringify writes the characters; Python's json escapes them by default, and
        # educational text is full of curly apostrophes.
        assert as_prompt_text({"note": "the student\u2019s caf\u00e9"}) == (
            '{"note":"the student\u2019s caf\u00e9"}'
        )

    def test_an_integral_float_reaches_it_as_an_integer(self) -> None:
        # JSON.stringify writes 2, not 2.0, however deeply the value is nested.
        assert as_prompt_text({"score": 2.0, "counts": [1.0, 2.5], "in": {"n": 3.0}}) == (
            '{"score":2,"counts":[1,2.5],"in":{"n":3}}'
        )

    def test_a_non_finite_float_reaches_it_as_null(self) -> None:
        # JSON.stringify writes null; Python's json writes NaN, which is not valid JSON.
        assert as_prompt_text({"x": float("nan"), "y": float("inf")}) == '{"x":null,"y":null}'

    def test_a_boolean_is_not_mistaken_for_a_number(self) -> None:
        assert as_prompt_text({"ok": True, "no": False}) == '{"ok":true,"no":false}'
