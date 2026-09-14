# Setup on Mac/Linux

You’ll need Python 3.10 or newer. To verify your version of Python, run the following code in the terminal:

```shell
python3 --version
```

## 1. Create a virtual environment

Creating an isolated environment is a best practice that prevents conflicts between Python packages used in this project and others on your system.

```shell
python3 -m venv .venv
source .venv/bin/activate
```

Remember to activate the virtual environment for each new shell session when working with Evaluators.

## 2. Install dependencies

The required packages are listed in the `requirements.txt` file.

```shell
pip install -r evals/requirements.txt
```

## 3. Set your API keys

Different evaluators call different providers, so which keys you need depends on which notebooks you plan to run:

| Key | Needed by | Where to get it |
| :-- | :-------- | :-------------- |
| `GOOGLE_API_KEY` | Most Student-Facing Text evaluators | [Google AI Studio](https://aistudio.google.com/) |
| `OPENAI_API_KEY` | Sentence Structure, Vocabulary Complexity, and all Feedback evaluators | [OpenAI Platform](https://platform.openai.com/) |
| `ANTHROPIC_API_KEY` | Math Standards Alignment, Critical Thinking | [Anthropic Console](https://console.anthropic.com/) |
| `KG_API_KEY` | Math Standards Alignment (Knowledge Graph standards lookup) | [Learning Commons Platform](https://platform.learningcommons.org) |

<!-- TODO: KG_API_KEY is the same credential the TypeScript SDK calls `learningCommonsApiKey`
     and demos/typescript calls `PLATFORM_API_KEY`. Standardize on LEARNING_COMMONS_API_KEY. -->

Set the key(s) you need as environment variables in your shell session:

```shell
export GOOGLE_API_KEY="your-key-here"
export OPENAI_API_KEY="sk-your-key-here"
export ANTHROPIC_API_KEY="sk-ant-your-key-here"
export KG_API_KEY="your-key-here"
```

## 4. Start Jupyter Lab

```shell
jupyter lab
```

This opens at `http://localhost:8888`. Browse into `evals/` and open the `example_notebook.ipynb` of the evaluator you want to try.
