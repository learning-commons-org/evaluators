import asyncio
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any

from dotenv import load_dotenv
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from learning_commons_evaluators import (
    BackgroundKnowledgeDemandsEvaluator,
    BaseEvaluator,
    EvaluationResult,
    GradeLevelAppropriatenessEvaluator,
    MeaningDirectnessEvaluator,
    OrganizationalStructureEvaluator,
    PurposeClarityEvaluator,
    ReferenceKnowledgeDemandsEvaluator,
    SentenceStructureEvaluator,
    VocabularyComplexityEvaluator,
    read_outcome,
)

load_dotenv()
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

GRADES = range(3, 13)
DEFAULT_GRADE = 5

# (class, takes grade_level). Grade Level Appropriateness determines a grade band from
# the text alone, so it is the one evaluator not given the selected grade.
EVALUATORS: list[tuple[type[BaseEvaluator], bool]] = [
    (GradeLevelAppropriatenessEvaluator, False),
    (BackgroundKnowledgeDemandsEvaluator, True),
    (VocabularyComplexityEvaluator, True),
    (SentenceStructureEvaluator, True),
    (MeaningDirectnessEvaluator, True),
    (PurposeClarityEvaluator, True),
    (OrganizationalStructureEvaluator, True),
    (ReferenceKnowledgeDemandsEvaluator, True),
]


@dataclass
class EvaluatorRun:
    name: str
    takes_grade: bool
    evaluation: EvaluationResult[Any] | None = None
    headline: str | None = None
    error: Exception | None = None

    @property
    def payload(self) -> dict[str, Any]:
        return self.evaluation.model_dump()["result"] if self.evaluation else {}

    @property
    def envelope_json(self) -> str:
        return self.evaluation.model_dump_json(indent=2) if self.evaluation else ""


async def run_one(
    cls: type[BaseEvaluator], takes_grade: bool, text: str, grade: int
) -> EvaluatorRun:
    run = EvaluatorRun(name=cls.metadata.name, takes_grade=takes_grade)
    # Constructed here, not at startup, so a missing key fails only this evaluator.
    try:
        evaluator = cls(google_api_key=GOOGLE_API_KEY, openai_api_key=OPENAI_API_KEY)
        inputs: dict[str, Any] = {"text": text}
        if takes_grade:
            inputs["grade_level"] = grade
        run.evaluation = await evaluator.evaluate(**inputs)
        run.headline = read_outcome(run.evaluation, cls.metadata.outcome).score
    except Exception as exc:
        run.error = exc
    return run


async def run_all(text: str, grade: int) -> list[EvaluatorRun]:
    return list(await asyncio.gather(*(run_one(cls, g, text, grade) for cls, g in EVALUATORS)))


app = FastAPI()
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


def render(
    request: Request,
    text: str = "",
    grade: int = DEFAULT_GRADE,
    runs: list[EvaluatorRun] | None = None,
    error: str | None = None,
    status_code: int = 200,
) -> HTMLResponse:
    context = {"text": text, "grade": grade, "grades": GRADES, "runs": runs, "error": error}
    return templates.TemplateResponse(request, "index.html", context, status_code=status_code)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return render(request)


@app.post("/", response_class=HTMLResponse)
async def evaluate(
    request: Request,
    grade: Annotated[int, Form(ge=3, le=12)],
    text: Annotated[str, Form()] = "",
) -> HTMLResponse:
    if not text.strip():
        return render(request, text, grade, error="Enter some text to evaluate.", status_code=400)
    return render(request, text, grade, runs=await run_all(text, grade))
