## **Evaluators** Code and Prompts

## **Requirements**

Please follow the detailed instructions in the top-level [README](../README.md) to set up your environment.

## **Quick Start**

Use the provided Makefile to quickly set up your environment and install dependencies with `make` tool.

### Install dependencies

```shell
make install
```

### Set your API keys

Set `GOOGLE_API_KEY` and `OPENAI_API_KEY` in the environment variable in your shell session, or add to `.env` file.

```shell
export GOOGLE_API_KEY="..."
export OPENAI_API_KEY="..."
```

### Run the Evaluator Code

You are now ready to run the evaluator examples. We recommend using a Jupyter Notebook for interactive exploration.

Start Jupyter Notebook:
```shell
make jupyter
```

Jupyter will open in your web browser (usually at http://localhost:8888).

1. In Jupyter file browser, double click on the evaluator you want to try.
2. Copy the text you want to evaluate into the last code cell of the notebook to try the evaluation of your text sample.
3. Use the toolbar to run all cells, or run each cell in sequence until the end.

    _If you prefer using an IDE with Python and Jupyter notebook support, such as VSCode with Microsoft's Python and Jupyter extensions, please refer to Microsoft's instructions for their installation and configuration._
