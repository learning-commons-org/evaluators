# Graphics Accuracy

Checks whether a math graphic (plot, chart, diagram, equation, or worked solution) correctly shows what its claim states. The claim is trusted; the image is under review. Early access; docs page pending.

- Schemas: [input](./input_schema.json), [output](./output_schema.json)
- [Fixtures](./fixtures.json), images in [`images/`](./images/) (from [MathVision](https://huggingface.co/datasets/MathLLMs/MathVision), MIT; see the repository [LICENSE](../../../../LICENSE.md))
- Prompts: [`system.txt`](./system.txt), [`user.txt`](./user.txt)

Validated on competition mathematics (MathVision); no per-grade measurement exists yet. No notebook yet.
