# `evals/`

Evaluators are thematically grouped into evaluator families:

- [Text Complexity](./text-complexity/)
- [Feedback](./feedback/)
- [Academic Standards](./academic-standards-alignment/)
- [Durable Skills](./durable-skills/)

Each evaluator family has its own directory and contains its evaluators as nested folders (e.g., the [Text Complexity](./text-complexity/) directory includes [Grade Level Appropriateness](./text-complexity/ela-reading/grade-level-appropriateness), [Background Knowledge Demands](./text-complexity/ela-reading/background-knowledge-demands), and other related evaluators).

Each evaluator subdirectory includes the following files:

- `config.json` — the evaluator's contract: its steps, models, prompts and grades
- Input schema
- Output schema
- Python notebook that demonstrates how to run the evaluator
- Validated prompts to use for that evaluator

Each family directory has a README listing its evaluators, and each evaluator directory has one linking its own schemas, notebook and prompts. For the full table of every evaluator with its docs, schemas, notebook and prompts in one place, see the [top-level README](../README.md#available-evaluators).
