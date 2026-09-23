"""Organizational Structure: the Organization dimension of qualitative text complexity.

One model call on Google, with the Flesch-Kincaid grade computed by ``textstat`` and bound
to ``{fk_score}``. Alone among this family's evaluators the contract pins the temperature
at 1 rather than 0. The verdict comes with a ``details`` payload — the factors found, the
scaffolding they call for, and the instructional openings they create.
"""

from learning_commons_evaluators.contracts import load_contract
from learning_commons_evaluators.evaluators.single_step import SingleStepEvaluator
from learning_commons_evaluators.schemas.text_complexity.ela_reading.organizational_structure import (
    EVALUATOR_ID,
    OrganizationalStructureInput,
    OrganizationalStructureOutput,
)


class OrganizationalStructureEvaluator(
    SingleStepEvaluator[OrganizationalStructureInput, OrganizationalStructureOutput]
):
    contract = load_contract(EVALUATOR_ID)
    input_model = OrganizationalStructureInput
    output_model = OrganizationalStructureOutput


__all__ = [
    "OrganizationalStructureEvaluator",
    "OrganizationalStructureInput",
    "OrganizationalStructureOutput",
]
