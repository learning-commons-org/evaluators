# Setup on Windows

You’ll need Python 3.10 or newer. To verify your version of python, run the following code in the terminal:

```shell
python --version
```

## 1. Create a virtual environment

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

## 2. Install dependencies

```cmd
pip install -r evals/requirements.txt
```

## 3. Set your API keys

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
