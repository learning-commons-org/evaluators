"""Bundled evaluator contracts (D1): the ``evals/`` registry as the package ships it.

``make generate-contracts`` copies each ``evals/<family>/<subject>/<evaluator>/`` contract —
``config.json``, its input and output schemas, and every prompt or rubric file it names —
into ``_generated/``, verbatim and sha256-checked. :func:`load_contract` reads one back as a
typed :class:`Contract`. Nothing here re-validates the registry at runtime (SDK spec §10):
the files are trusted as the build step bundled them.
"""

from learning_commons_evaluators.contracts.loader import (
    Condition,
    Contract,
    EvaluatorInfo,
    Generation,
    Implementation,
    ModelSpec,
    Outcome,
    Placeholder,
    PostTransform,
    Preprocessing,
    Prompt,
    PromptMessage,
    Step,
    contract_path,
    list_contract_ids,
    load_contract,
)

__all__ = [
    "Condition",
    "Contract",
    "EvaluatorInfo",
    "Generation",
    "Implementation",
    "ModelSpec",
    "Outcome",
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
