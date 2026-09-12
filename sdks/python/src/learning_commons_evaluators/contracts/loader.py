"""Reading a bundled contract into typed objects.

The models below mirror ``evals/_schemas/config.schema.json`` field for field, with the
same names, so a reader of either can follow the other. They ignore keys they do not know
rather than rejecting them: a registry that gains a field must not break an installed SDK,
and registry-side CI owns the strict check.
"""

from __future__ import annotations

import json
from functools import cache
from importlib import resources
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from learning_commons_evaluators.providers.base import Provider

if TYPE_CHECKING:
    from importlib.abc import Traversable
else:
    try:
        from importlib.resources.abc import Traversable
    except ImportError:  # Python 3.10
        from importlib.abc import Traversable

#: The package directory the build step writes into.
BUNDLE_DIR = "_generated"

#: The file the loader looks for; a directory holding one is a contract.
CONFIG_FILE = "config.json"


class _ContractModel(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True, populate_by_name=True)


class EvaluatorInfo(_ContractModel):
    """``config.evaluator``: the three-layer identity plus the human-readable facts."""

    id: str
    stable_id: str
    id_history: list[str] = Field(default_factory=list)
    name: str
    description: str
    supported_grades: list[str]

    @property
    def slug(self) -> str:
        """The last id segment, which names the Python module and the step convention."""
        return self.id.rsplit(".", 1)[-1]


class Condition(_ContractModel):
    """A step or preprocessing entry applies only when ``input`` takes one of ``values``."""

    input: str
    values: list[str] = Field(alias="in")

    @field_validator("values", mode="before")
    @classmethod
    def _as_strings(cls, raw: Any) -> Any:
        # The schema admits numbers; inputs are compared as the strings the caller passes.
        return [str(v) for v in raw] if isinstance(raw, list) else raw

    def holds(self, fields: dict[str, str]) -> bool:
        return fields.get(self.input) in self.values


class PromptMessage(_ContractModel):
    role: Literal["system", "user", "assistant"]
    source_path: str
    sha256: str | None = None


class Placeholder(_ContractModel):
    """Where one ``{name}`` in a prompt is filled from.

    ``source`` takes exactly four forms: ``input`` (the caller input of the same name),
    ``input.<field>``, ``preprocessing.<output>``, and ``steps.<id>.output``.
    """

    required: bool
    source: str
    note: str | None = None


class Prompt(_ContractModel):
    messages: list[PromptMessage]
    placeholders: dict[str, Placeholder]


class ModelSpec(_ContractModel):
    provider: Provider
    name: str
    alias: str | None = None


class Generation(_ContractModel):
    """``temperature`` is ``None`` when the parameter must be omitted entirely."""

    temperature: float | None = None


class Parser(_ContractModel):
    kind: str


class Step(_ContractModel):
    """One entry of ``config.steps``. An ``llm`` step always carries ``prompt`` and ``model``."""

    id: str
    type: Literal["llm", "api"]
    optional: bool = False
    description: str | None = None
    prompt: Prompt | None = None
    model: ModelSpec | None = None
    generation: Generation | None = None
    parser: Parser | None = None
    condition: Condition | None = None
    required_credentials: list[str] = Field(default_factory=list)

    @property
    def temperature(self) -> float | None:
        return self.generation.temperature if self.generation is not None else None


class PostTransform(_ContractModel):
    type: str
    precision: int | None = None


class Implementation(_ContractModel):
    """The library function one language calls for a computation entry."""

    library: str
    function: str
    post_transform: PostTransform | None = None


class Preprocessing(_ContractModel):
    """One entry of ``config.preprocessing``: a computation or an API call producing ``output``."""

    id: str
    type: Literal["api", "computation"]
    kind: str
    description: str | None = None
    input: str | None = None
    output: str | None = None
    required_credentials: list[str] = Field(default_factory=list)
    implementation: dict[str, Implementation] = Field(default_factory=dict)
    endpoint: str | None = None
    params: dict[str, Any] = Field(default_factory=dict)
    auth: str | None = None
    pagination: str | None = None
    source_path: str | None = None
    sha256: str | None = None
    condition: Condition | None = None

    @property
    def python(self) -> Implementation | None:
        """This SDK's binding, when the entry declares one."""
        return self.implementation.get("python")


class Outcome(_ContractModel):
    """Which output properties carry the verdict and its rationale."""

    score: str
    reasoning: str


class Fixtures(_ContractModel):
    path: str | None = None
    tolerance: dict[str, Any] = Field(default_factory=dict)


class Contract(_ContractModel):
    """One evaluator's registry definition, with its schemas and prompt texts attached."""

    evaluator: EvaluatorInfo
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    preprocessing: list[Preprocessing] = Field(default_factory=list)
    steps: list[Step]
    outcome: Outcome | None = None
    fixtures: Fixtures | None = None
    #: Every file the contract names, by its ``source_path``, verbatim.
    documents: dict[str, str] = Field(default_factory=dict)

    def step(self, step_id: str) -> Step:
        """The step declared under ``step_id``, or a failure naming the one that was expected."""
        for step in self.steps:
            if step.id == step_id:
                return step
        raise LookupError(f'Step "{step_id}" not found in {self.evaluator.name} config.json')

    def preprocessing_entry(self, entry_id: str) -> Preprocessing:
        for entry in self.preprocessing:
            if entry.id == entry_id:
                return entry
        raise LookupError(
            f'Preprocessing "{entry_id}" not found in {self.evaluator.name} config.json'
        )

    def document(self, source_path: str) -> str:
        """The text of a prompt or rubric file the contract names."""
        try:
            return self.documents[source_path]
        except KeyError:
            raise LookupError(
                f'{self.evaluator.name} config.json names "{source_path}", which was not bundled.'
            ) from None

    @property
    def required_credentials(self) -> list[str]:
        """The non-LLM credentials declared across every entry that can run.

        An optional step is excluded: it runs only when a caller opts in, so requiring its
        credential at construction would demand a key for a call that never happens.
        """
        seen: list[str] = []
        entries: list[Preprocessing | Step] = [
            *self.preprocessing,
            *(s for s in self.steps if not s.optional),
        ]
        for entry in entries:
            for key in entry.required_credentials:
                if key not in seen:
                    seen.append(key)
        return seen

    @property
    def providers(self) -> list[Provider]:
        """Distinct LLM providers of the non-optional steps, in declared order."""
        seen: list[Provider] = []
        for step in self.steps:
            if step.optional or step.model is None:
                continue
            if step.model.provider not in seen:
                seen.append(step.model.provider)
        return seen


def _bundle_root() -> Traversable:
    return resources.files("learning_commons_evaluators.contracts") / BUNDLE_DIR


def contract_path(evaluator_id: str) -> Traversable:
    """The bundled directory for an evaluator id, one path segment per dotted id segment."""
    path = _bundle_root()
    for segment in evaluator_id.split("."):
        path = path / segment
    return path


def _walk_configs(directory: Traversable, prefix: list[str]) -> list[str]:
    ids: list[str] = []
    if (directory / CONFIG_FILE).is_file():
        ids.append(".".join(prefix))
    for child in directory.iterdir():
        if child.is_dir():
            ids.extend(_walk_configs(child, [*prefix, child.name]))
    return ids


def list_contract_ids() -> list[str]:
    """Every bundled evaluator id, sorted."""
    root = _bundle_root()
    if not root.is_dir():
        return []
    return sorted(_walk_configs(root, []))


def _read_json(path: Traversable) -> Any:
    return json.loads(path.read_bytes().decode("utf-8"))


def _resolve_ref(config_dir: Traversable, declared: Any, key: str) -> dict[str, Any]:
    """A schema the config declares inline or via ``$ref`` to a sibling file."""
    if not isinstance(declared, dict):
        raise ValueError(f"{key} must be an object")
    ref = declared.get("$ref")
    if isinstance(ref, str):
        loaded = _read_json(config_dir / ref)
        if not isinstance(loaded, dict):
            raise ValueError(f"{key} {ref!r} must hold an object")
        return loaded
    return declared


@cache
def load_contract(evaluator_id: str) -> Contract:
    """The bundled contract for ``evaluator_id``, read once and cached.

    :raises FileNotFoundError: when no contract is bundled under that id.
    """
    config_dir = contract_path(evaluator_id)
    config_file = config_dir / CONFIG_FILE
    if not config_file.is_file():
        raise FileNotFoundError(
            f"No bundled contract for {evaluator_id!r}. Run `make generate-contracts`."
        )
    raw = _read_json(config_file)

    documents: dict[str, str] = {}
    for step in raw.get("steps", []):
        for message in (step.get("prompt") or {}).get("messages", []):
            source = message["source_path"]
            documents[source] = (config_dir / source).read_bytes().decode("utf-8")
    for entry in raw.get("preprocessing", []) or []:
        source = entry.get("source_path")
        if source:
            documents[source] = (config_dir / source).read_bytes().decode("utf-8")

    return Contract.model_validate(
        {
            **raw,
            "input_schema": _resolve_ref(config_dir, raw.get("input_schema"), "input_schema"),
            "output_schema": _resolve_ref(config_dir, raw.get("output_schema"), "output_schema"),
            "documents": documents,
        }
    )


__all__ = [
    "BUNDLE_DIR",
    "CONFIG_FILE",
    "Condition",
    "Contract",
    "EvaluatorInfo",
    "Fixtures",
    "Generation",
    "Implementation",
    "ModelSpec",
    "Outcome",
    "Parser",
    "Placeholder",
    "PostTransform",
    "Preprocessing",
    "Prompt",
    "PromptMessage",
    "Step",
    "contract_path",
    "list_contract_ids",
    "load_contract",
]
