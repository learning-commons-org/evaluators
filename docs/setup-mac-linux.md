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

We are using **both** OpenAI and Google Gemini for different evaluators. You need API keys from both platforms:

- OpenAI: [https://platform.openai.com/](https://platform.openai.com/)
- Gemini: [https://aistudio.google.com/](https://aistudio.google.com/)

Set the key(s) as environment variables in your shell session:

```shell
export OPENAI_API_KEY="sk-your-key-here"
export GOOGLE_API_KEY="your-key-here"
```
