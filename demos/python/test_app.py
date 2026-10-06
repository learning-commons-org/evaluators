import asyncio
import re

import pytest
from fastapi.testclient import TestClient
from learning_commons_evaluators import (
    BackgroundKnowledgeDemandsEvaluator,
    ConfigurationError,
    EvaluationMetadata,
    EvaluationResult,
    EvaluationTokenUsage,
    GradeLevelAppropriatenessEvaluator,
    MeaningDirectnessEvaluator,
    OrganizationalStructureEvaluator,
    PurposeClarityEvaluator,
    ReferenceKnowledgeDemandsEvaluator,
    SentenceStructureEvaluator,
    TelemetryOptions,
    VocabularyComplexityEvaluator,
    get_evaluators,
)

import app

TEXT = "Some text to evaluate."


def make_stub(real_cls, calls, fail=None, keys_seen=None):
    outcome = real_cls.metadata.outcome

    class Stub:
        metadata = real_cls.metadata

        def __init__(self, **keys):
            if keys_seen is not None:
                keys_seen[real_cls.metadata.name] = keys
            if fail is not None:
                raise fail

        async def evaluate(self, **inputs):
            calls[real_cls.metadata.name] = inputs
            return EvaluationResult(
                evaluator=real_cls.metadata.id,
                result={outcome.score: "stub_score", outcome.reasoning: "stub reasoning"},
                metadata=EvaluationMetadata(
                    model="stub:model",
                    processing_time_ms=1,
                    token_usage=EvaluationTokenUsage(input_tokens=3, output_tokens=4),
                ),
            )

    return Stub


@pytest.fixture
def calls():
    return {}


@pytest.fixture
def keys_seen():
    return {}


@pytest.fixture
def stubbed(monkeypatch, calls, keys_seen):
    real = list(app.EVALUATORS)

    def install(failing=None, error=None):
        monkeypatch.setattr(
            app,
            "EVALUATORS",
            [
                (
                    make_stub(
                        cls, calls, fail=error if cls is failing else None, keys_seen=keys_seen
                    ),
                    takes_grade,
                )
                for cls, takes_grade in real
            ],
        )

    install()
    return install


@pytest.fixture
def client():
    return TestClient(app.app)


def test_index_offers_grades_3_to_12_prefilled_with_the_sample_text_and_grade_4(client):
    body = client.get("/").text
    assert re.search(rf'<textarea name="text"[^>]*>{re.escape(app.DEFAULT_TEXT)}</textarea>', body)
    assert app.DEFAULT_TEXT.startswith("The sun is the star at the center of the Solar System.")
    assert re.search(r'<option[^>]*value="4"[^>]*selected', body)
    assert len(re.findall(r"<option[^>]*selected", body)) == 1
    assert "Grade 3" in body
    assert "Grade 12" in body
    assert "Grade 2" not in body
    assert "Grade 13" not in body


def test_blank_text_is_rejected_before_any_evaluator_runs(client, stubbed, calls):
    response = client.post("/", data={"text": "   ", "grade": 5})
    assert response.status_code == 400
    assert "Enter some text to evaluate." in response.text
    assert calls == {}


def test_out_of_range_grade_is_rejected(client):
    assert client.post("/", data={"text": TEXT, "grade": 13}).status_code == 422


def test_one_failing_evaluator_does_not_affect_the_others(client, stubbed):
    stubbed(SentenceStructureEvaluator, ConfigurationError("missing openai_api_key"))

    runs = asyncio.run(app.run_all(TEXT, 5))
    failed = [run for run in runs if run.error is not None]
    succeeded = [run for run in runs if run.evaluation is not None]
    assert len(runs) == 8
    assert [run.name for run in failed] == [SentenceStructureEvaluator.metadata.name]
    assert isinstance(failed[0].error, ConfigurationError)
    assert len(succeeded) == 7
    assert all(run.headline == "stub_score" for run in succeeded)

    response = client.post("/", data={"text": TEXT, "grade": 5})
    assert response.status_code == 200
    assert "ConfigurationError" in response.text
    assert "missing openai_api_key" in response.text
    assert response.text.count("<details") == 8


def test_only_grade_level_appropriateness_runs_without_the_grade(client, stubbed, calls):
    client.post("/", data={"text": TEXT, "grade": 7})
    assert len(calls) == 8
    gla = GradeLevelAppropriatenessEvaluator.metadata.name
    assert calls.pop(gla) == {"text": TEXT}
    assert all(inputs == {"text": TEXT, "grade_level": 7} for inputs in calls.values())


def test_every_evaluator_is_constructed_with_both_configured_keys(
    client, stubbed, keys_seen, monkeypatch
):
    monkeypatch.setattr(app, "GOOGLE_API_KEY", "google-key")
    monkeypatch.setattr(app, "OPENAI_API_KEY", "openai-key")
    monkeypatch.setattr(app, "TELEMETRY_LEARNING_COMMONS_API_KEY", "")
    client.post("/", data={"text": TEXT, "grade": 5})
    assert len(keys_seen) == 8
    expected = {"google_api_key": "google-key", "openai_api_key": "openai-key", "telemetry": True}
    assert all(keys == expected for keys in keys_seen.values())


def test_a_learning_commons_key_attributes_every_evaluators_telemetry(
    client, stubbed, keys_seen, monkeypatch
):
    monkeypatch.setattr(app, "TELEMETRY_LEARNING_COMMONS_API_KEY", "lc-key")
    client.post("/", data={"text": TEXT, "grade": 5})
    assert len(keys_seen) == 8
    expected = TelemetryOptions(learning_commons_api_key="lc-key")
    assert all(keys["telemetry"] == expected for keys in keys_seen.values())


def test_only_grade_level_appropriateness_carries_the_text_alone_note(client, stubbed):
    body = client.post("/", data={"text": TEXT, "grade": 5}).text
    assert body.count("Judged on the text alone") == 1


def test_submitted_text_and_grade_are_kept_in_the_form(client, stubbed):
    body = client.post("/", data={"text": TEXT, "grade": 7}).text
    assert f">{TEXT}</textarea>" in body
    assert re.search(r'<option[^>]*value="7"[^>]*selected', body)


def test_demo_runs_exactly_the_sdk_text_complexity_family():
    ids = {cls.metadata.id for cls, _ in app.EVALUATORS}
    assert ids == {m.id for m in get_evaluators() if m.id.startswith("text_complexity.")}
    assert len(ids) == 8


def test_results_render_in_the_fixed_display_order(client, stubbed):
    body = client.post("/", data={"text": TEXT, "grade": 5}).text
    expected = [
        GradeLevelAppropriatenessEvaluator,
        BackgroundKnowledgeDemandsEvaluator,
        VocabularyComplexityEvaluator,
        SentenceStructureEvaluator,
        MeaningDirectnessEvaluator,
        PurposeClarityEvaluator,
        OrganizationalStructureEvaluator,
        ReferenceKnowledgeDemandsEvaluator,
    ]
    rendered = re.findall(r"<strong>([^<]+)</strong>", body)
    assert rendered == [cls.metadata.name for cls in expected]
