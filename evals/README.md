# `evals/`

Evaluators are thematically grouped into evaluator families:

- [Text Complexity](./text-complexity/)
- [Feedback](./feedback/)
- [Academic Standards](./academic-standards-alignment/)
- [Durable Skills](./durable-skills/)
- [Graphics](./graphics/)

Each evaluator family has its own directory and contains its evaluators as nested folders (e.g., the [Text Complexity](./text-complexity/) directory includes [Grade Level Appropriateness](./text-complexity/ela-reading/grade-level-appropriateness), [Background Knowledge Demands](./text-complexity/ela-reading/background-knowledge-demands), and other related evaluators).

## For each evaluator

Each evaluator subdirectory includes the following files:

- `config.json` — the evaluator's contract: its steps, models, prompts and grades
- Input schema
- Output schema
- Python notebook that demonstrates how to run the evaluator
- Validated prompts to use for that evaluator

## Resources

- [Quickstart](../README.md#quickstart)
- [All available evaluators](../README.md#available-evaluators) with docs, schemas, and more
