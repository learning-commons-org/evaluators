# [Vocabulary Complexity](https://docs.learningcommons.org/evaluators/text-complexity-evaluators/vocabulary-complexity)

Evaluates the complexity of a text's vocabulary relative to its target grade.

- Schemas: [input](./input_schema.json), [output](./output_schema.json)
- [Python notebook](./example_notebook.ipynb)
- Prompts: [`background-knowledge.txt`](./background-knowledge.txt), [`grades-3-4-system.txt`](./grades-3-4-system.txt), [`grades-3-4-user.txt`](./grades-3-4-user.txt), [`other-grades-system.txt`](./other-grades-system.txt), [`other-grades-user.txt`](./other-grades-user.txt)
- Model used: Each model runs at its default settings, with no temperature set:
  - GPT-6-luna (Step 1, all grades)
  - Gemini 3.8 Flash (Step 2, grades 3–4)
  - GPT-6-luna (Step 2, grades 5–12)
