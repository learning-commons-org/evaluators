"""Graphics Accuracy: does a math graphic correctly show what its claim states?

The claim is the specification: a statement about the image, or a question with its
expected answer written as ``Question: "…" The answer is ….`` (see
:func:`compose_graphics_accuracy_claim`). ``image_paths`` is a one-item list holding the
local path of the image under review; its bytes are read in the caller's environment,
checked against the contract's ``x-image`` bounds, and attached to the model request ahead
of the text.

One model call on Google, so the flow comes from :class:`SingleStepEvaluator`; the model,
the omitted temperature, the prompt inputs and the attachment are read from the contract.
The verdict is ``is_correct``; ``basis`` says whether a false verdict came from a derivation
that disagreed (``contradicted``), one that could not be completed (``unverified``), or a
defect in the image itself (``defective``), which ``defects`` lists.
"""

from learning_commons_evaluators.contracts import load_contract
from learning_commons_evaluators.evaluators.single_step import SingleStepEvaluator
from learning_commons_evaluators.schemas.graphics.math.graphics_accuracy import (
    EVALUATOR_ID,
    GraphicsAccuracyInput,
    GraphicsAccuracyOutput,
)


class GraphicsAccuracyEvaluator(SingleStepEvaluator[GraphicsAccuracyInput, GraphicsAccuracyOutput]):
    contract = load_contract(EVALUATOR_ID)
    input_model = GraphicsAccuracyInput
    output_model = GraphicsAccuracyOutput


def compose_graphics_accuracy_claim(question: str, answer: str) -> str:
    """The ``claim`` text for a question with an expected answer.

    Byte-for-byte the text the evaluator was measured with, so a caller who has a problem
    and its answer key gets the measured behaviour rather than a paraphrase of it.
    Surrounding whitespace is trimmed from both parts; nothing else is changed.
    """
    return f'Question: "{question.strip()}" The answer is {answer.strip()}.'


__all__ = [
    "GraphicsAccuracyEvaluator",
    "GraphicsAccuracyInput",
    "GraphicsAccuracyOutput",
    "compose_graphics_accuracy_claim",
]
