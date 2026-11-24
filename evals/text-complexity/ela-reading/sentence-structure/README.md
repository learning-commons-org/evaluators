# [Sentence Structure](https://docs.learningcommons.org/evaluators/text-complexity-evaluators/sentence-structure)

Evaluates the sentence-structure complexity of a text relative to its target grade.

- Schemas: [input](./input_schema.json), [output](./output_schema.json)
- [Python notebook](./example_notebook.ipynb)
- Prompts: [`analysis-system.txt`](./analysis-system.txt), [`analysis-user.txt`](./analysis-user.txt), [`complexity-system.txt`](./complexity-system.txt), [`complexity-user.txt`](./complexity-user.txt)
- Model used: GPT-6-luna for grades 3–4 (`gpt-6-luna`) and GPT-5.5 for grades 5–12 (`gpt-5.5-2026-04-23`), both at reasoning effort none
- Rubrics bound into the complexity prompt, one per grade: [`rubric-grade-3.txt`](./rubric-grade-3.txt), [`rubric-grade-4.txt`](./rubric-grade-4.txt), [`rubric-grades-5-12.txt`](./rubric-grades-5-12.txt)
