"""Graphics Complexity: how demanding a passage's graphics are for the target grade.

``image_paths`` holds one local image path per graphic in scope (up to five); each file is
read in the caller's environment, checked against the contract's ``x-image`` bounds, and
attached to the model request after the text. ``figure_labels`` optionally names them, in
the same order; omitted, they are "Image 1" to "Image N".

One model call on Google, so the flow comes from :class:`SingleStepEvaluator`; the model,
temperature, preprocessing, prompt inputs and attachment are read from the contract. The
model also rates each graphic and any that must be read together; those working fields are
marked ``x-model-only`` in the contract, so the model is asked for
:class:`GraphicsComplexityResponse` and the caller receives :class:`GraphicsComplexityOutput`.
"""

from learning_commons_evaluators.contracts import load_contract
from learning_commons_evaluators.errors import InputValidationError
from learning_commons_evaluators.evaluators.inputs import InputValue
from learning_commons_evaluators.evaluators.single_step import SingleStepEvaluator
from learning_commons_evaluators.schemas.graphics.ela.graphics_complexity import (
    EVALUATOR_ID,
    GraphicsComplexityInput,
    GraphicsComplexityOutput,
    GraphicsComplexityResponse,
)


class GraphicsComplexityEvaluator(
    SingleStepEvaluator[GraphicsComplexityInput, GraphicsComplexityOutput]
):
    contract = load_contract(EVALUATOR_ID)
    input_model = GraphicsComplexityInput
    output_model = GraphicsComplexityOutput
    response_model = GraphicsComplexityResponse

    def _prepare_inputs(self, values: dict[str, InputValue]) -> dict[str, InputValue]:
        """``figure_labels`` as the model reads it: one distinct label per image, in order.

        Omitted, the images are labelled "Image 1" to "Image N", as the input schema says.
        The model rates each graphic under its label and names labels when graphics must be
        read together, so a count that does not match the images, or a repeated label, would
        leave it rating graphics it cannot tell apart.

        :raises InputValidationError: if ``figure_labels`` does not give one distinct,
            non-empty label per image.
        """
        count = len(values["image_paths"])
        given = values.get("figure_labels")
        if given is None:
            return {**values, "figure_labels": ", ".join(f"Image {i + 1}" for i in range(count))}
        assert isinstance(given, str)  # a string input, validated as one
        labels = [label.strip() for label in given.split(",")]
        if len(labels) != count or not all(labels) or len(set(labels)) != len(labels):
            raise InputValidationError(
                "figure_labels needs one distinct, non-empty label per image, comma-separated "
                f"in image_paths order; received {len(labels)} for {count} "
                f"image{'' if count == 1 else 's'}."
            )
        return {**values, "figure_labels": ", ".join(labels)}


__all__ = [
    "GraphicsComplexityEvaluator",
    "GraphicsComplexityInput",
    "GraphicsComplexityOutput",
]
