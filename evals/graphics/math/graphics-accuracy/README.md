# Graphics Accuracy

Checks whether a math graphic (plot, chart, diagram, equation, or worked solution) correctly shows what its claim states. The claim is trusted; the image is under review. Early access; docs page pending.

`is_correct` is the pass/fail verdict (`outcome.score`); for a false verdict, `basis` says why: `contradicted`, `unverified` or `defective`.

- Schemas: [input](./input_schema.json), [output](./output_schema.json)
- [Fixtures](./fixtures.json), images in [`images/`](./images/) (synthetic figures drawn for these fixtures)
- [Python notebook](./example_notebook.ipynb)
- Prompts: [`system.txt`](./system.txt), [`user.txt`](./user.txt)
