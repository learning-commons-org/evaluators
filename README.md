# Evaluators

<img style="width:100%" alt="Evaluators project banner logo" src="https://raw.githubusercontent.com/learning-commons-org/.github/refs/heads/main/assets/evals_hero_2.jpg" />

<p align="center">
  <a href="https://platform.learningcommons.org/apps/evaluators/playground" target="_blank">Try it in the Playground </a>
   •
  <a href="https://docs.learningcommons.org/evaluators/getting-started/quickstart" target="_blank">Quickstart</a>
  •
  <a href="https://docs.learningcommons.org/evaluators/understanding-evaluators/core-concepts" target="_blank">Core concepts</a>
</p>

Evaluators help you to measure the attributes of LLM-generated text through the lens of learning science.

We build learning-science-backed systems that follow LLM-as-a-judge methodology and can be directly integrated to your product or evaluation stack.

Use cases include:

- **Feature optimization**: Use fine-grained literacy evaluation to sharpen and consistently deliver a feature’s AI-generated content so it aligns with pedagogy and your goals.
- **Maintaining performance**: Ensure content is generated as expected by using the evaluators as product analytics for your LLM output.
- **Model selection**: Make a confident decision about which model is right for your product by testing the output of models you’re considering.

Evaluators and the supporting datasets are built in collaboration with leading literacy experts from Student Achievement Partners and the Achievement Network.

## Repository contents

| Path                      | Description                                                      |
| :------------------------ | :--------------------------------------------------------------- |
| [`evals`](./evals/)       | Evaluators code and prompts                                      |
| [`datasets`](./datasets/) | Expert annotated datasets used to create and validate evaluators |
| [`scripts`](./scripts/)   | Repo check harness — run `python3 scripts/check.py --fix` before committing (see [scripts/README](./scripts/README.md)) |
| [`LICENSE`](./LICENSE.md) | Open source license details                                      |

Check out the [Evaluators docs](https://docs.learningcommons.org/evaluators) for complete setup instructions and usage examples.

## Try the evaluators

You can test the evaluators with your own text in the [Evaluators Playground](https://platform.learningcommons.org/apps/evaluators/playground) on the Learning Commons Platform.

## Quickstart

To use the evaluators, clone the repository and follow the instructions below.

If you’d like to download or access our evaluators and datasets directly, follow the links below.

- Evaluators literacy package
  - [Prompts and notebooks](./evals) — grouped by domain (`evals/literacy/`, `evals/prompts/`)
- Datasets
  - [Learning Commons annotations of CLEAR for qualitative text complexity v1.0 2025-09-02.csv](https://aidt-evaluators-files-public-prod.s3.us-west-2.amazonaws.com/Learning+Commons+annotations+of+CLEAR+for+qualitative+text+complexity+v1.0+2025-09-02.csv)

## Requirements

We rely on the Python interpreter to power the evaluators. All examples and tutorials are provided as Python code snippets.

## Setup on Mac/Linux

You’ll need Python 3.10 or newer. To verify your version of Python, run the following code in the terminal:

```shell
python3 --version
```

### 1. Create a virtual environment

Creating an isolated environment is a best practice that prevents conflicts between Python packages used in this project and others on your system.

```shell
python3 -m venv .venv
source .venv/bin/activate
```

Remember to activate the virtual environment for each new shell session when working with Evaluators.

### 2. Install dependencies

The required packages are listed in the `requirements.txt` file.

```shell
pip install -r evals/requirements.txt
```

### 3. Set your API keys

We are using **both** OpenAI and Google Gemini for different evaluators. You need API keys from both platforms:

- OpenAI: [https://platform.openai.com/](https://platform.openai.com/)
- Gemini: [https://aistudio.google.com/](https://aistudio.google.com/)

Set the key(s) as environment variables in your shell session:

```shell
export OPENAI_API_KEY="sk-your-key-here"
export GOOGLE_API_KEY="your-key-here"
```

</details>
<details>
<summary>Setup on Windows</summary>

## Setup on Windows

You’ll need Python 3.10 or newer. To verify your version of python, run the following code in the terminal:

```shell
python --version
```

### 1. Create a virtual environment

Open a Command Prompt and run:

```cmd
python -m venv .venv
.venv\Scripts\activate
```

Or in PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Remember to activate the virtual environment for each new shell session when working with Evaluators.

### 2. Install dependencies

```cmd
pip install -r evals/requirements.txt
```

### 3. Set your API keys

Get your API keys from:

- OpenAI: [https://platform.openai.com/](https://platform.openai.com/)
- Gemini: [https://aistudio.google.com/](https://aistudio.google.com/)

Set the key(s) as environment variables:

In Command Prompt:

```cmd
set OPENAI_API_KEY=sk-your-key-here
set GOOGLE_API_KEY=your-key-here
```

In PowerShell:

```powershell
$env:OPENAI_API_KEY="sk-your-key-here"
$env:GOOGLE_API_KEY="your-key-here"
```

</details>

## Run the Evaluators' code

You are now ready to run the evaluator examples. We recommend using a Jupyter Notebook for interactive exploration.

1. **Start Jupyter Notebooks Lab:**

```shell
jupyter lab
```

Jupyter will open in your web browser (usually at `http://localhost:8888`).

2. Browse into the `evals` folder, then double click on the evaluator you want to try.
3. You can now copy the text you want to evaluate into the last code cell of the notebook to run an evaluator on your text sample.

If you prefer using an IDE with Python and Jupyter notebook support, such as VSCode with Microsoft's Python and Jupyter extensions, please refer to Microsoft's instructions for their installation and configuration.

## Support & feedback

We want to hear from you. For questions or feedback, please [open an issue](https://github.com/learning-commons-org/evaluators/issues) or reach out to us at [support@learningcommons.org](mailto:support@learningcommons.org)

## Stay up to date

Sign up for a <a href="https://platform.learningcommons.org" target="_blank">Learning Commons account</a> to receive news about the latest Evaluators updates, and releases.

## Reporting security issues

If you believe you have found a security issue, please responsibly disclose by contacting us at [security@learningcommons.org](mailto:security@learningcommons.org).

## Disclaimer

Use of the resources provided in this repository is subject to [our Terms of Use](https://learningcommons.org/terms-of-use/).
