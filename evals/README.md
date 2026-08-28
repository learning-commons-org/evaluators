# Evaluators code and prompts

- [Requirements](#requirements)
- [Quickstart](#quickstart)

  | Evaluator                   | Code                                                     | Prompts                                           |
  | --------------------------- | -------------------------------------------------------- | ------------------------------------------------- |
  | Grade Level Appropriateness | [Jupyter Notebook](./student-facing-text/ela-reading/grade-level-appropriateness/example_notebook.ipynb) | [Prompts](./student-facing-text/ela-reading/grade-level-appropriateness/) |
  | Sentence Structure          | [Jupyter Notebook](./sentence_structure_evaluator.ipynb) | [Prompts](./prompts/sentence-structure/)          |
  | Vocabulary                  | [Jupyter Notebook](./vocabulary_evaluator.ipynb)         | [Prompts](./prompts/vocabulary/)                  |
  | Background Knowledge Demands | [Jupyter Notebook](./student-facing-text/ela-reading/background-knowledge-demands/example_notebook.ipynb) | [Prompts](./student-facing-text/ela-reading/background-knowledge-demands/) |
  | Conventionality             | [Jupyter Notebook](./conventionality_evaluator.ipynb)    | [Prompts](./prompts/conventionality/)             |
  | Purpose                     | [Jupyter Notebook](./purpose_evaluator.ipynb)            | [Prompts](./prompts/purpose/)                     |

## Requirements

[Set up your environment](../README.md) and install your dependencies:

```shell
make install
```

Next, set your API keys as environment variables in your shell session:

```shell
export GOOGLE_API_KEY="..."
export OPENAI_API_KEY="..."
```

You can also add these environment variables to an `.env` file.

## Quickstart

Use the provided Makefile to quickly set up your environment and install dependencies with `make` tool.

### Install dependencies

```shell
make install
```

Next, start a Jupyter Notebook so you can run the evaluator examples and easily interact with your outputs:

Start Jupyter Notebook:

```shell
make jupyter
```

Jupyter will open in your web browser (usually at http://localhost:8888).

1. In Jupyter file browser, double click on the evaluator you want to try.
2. Copy the text you want to evaluate into the last code cell of the notebook to try the evaluation of your text sample.
3. Use the toolbar to run all cells, or run each cell in sequence until the end.

_If you prefer using an IDE with Python and Jupyter notebook support, such as VSCode with Microsoft's Python and Jupyter extensions, please refer to Microsoft's instructions for their installation and configuration._
