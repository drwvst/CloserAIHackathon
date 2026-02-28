# CloserAI Hackathon Project

Agentic web app for realtors to manage clients and run one-shot listing analyses.

## Quick Start

### 1) Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
```

### 2) Install dependencies

```bash
pip install -r requirements.txt
```

### 3) Configure Streamlit secrets

Create `.streamlit/secrets.toml` in the repo root:

```toml
MONGO_URI = "mongodb+srv://<username>:<password>@<cluster-url>/"
OPENAI_API_KEY = "sk-..." # optional
```

⚠️ Do **not** include `EOF` in the file. That token is only used when creating files from shell heredocs.

### 4) Run the app

```bash
streamlit run website/app.py
```

## Common Errors

- **`ModuleNotFoundError: No module named 'ZillowScraper'`**
  - Fixed in code by adding the repo root to `sys.path` during app startup.

- **`StreamlitSecretNotFoundError` / TOML parse errors**
  - Recheck `.streamlit/secrets.toml` formatting (every key must have a quoted value).
  - Remove any trailing `EOF` line.
  - You can also set `MONGO_URI` as an environment variable if secrets parsing fails.

## Basic smoke test

```bash
python -m py_compile website/app.py website/agent.py website/auth.py website/database.py ZillowScraper.py
```
