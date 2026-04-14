# LLM Output Arbitration System

Multi-agent arbitration pipeline that critiques a candidate LLM response with
specialized evaluators, then synthesizes those critiques into a confidence-based
verdict.

## What This Includes

- FastAPI service with a production-style API shape.
- Three critic roles:
  - Factual Accuracy Critic
  - Logical Consistency Critic
  - Completeness Critic
- Strict, typed output models using Pydantic.
- SQLite + SQLAlchemy audit logging of requests and final verdicts.
- OpenRouter-backed critic calls for factual/logical/completeness evaluation.
- Deterministic fallback heuristics so the system still runs without API keys.

## Tech Stack

- Python 3.11+
- FastAPI
- Pydantic v2
- SQLAlchemy
- pytest
- OpenRouter (LLM gateway)

The architecture remains provider-agnostic at the critic interface while using
OpenRouter as the Phase 2 execution layer.

## Quick Start

1. Create and activate a virtual environment:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies:

   ```bash
   pip install -e ".[dev]"
   ```

3. Configure environment variables:

   ```bash
   export OPENROUTER_API_KEY="your_openrouter_api_key"
   export OPENROUTER_MODEL_FACTUAL="openai/gpt-4o-mini"
   export OPENROUTER_MODEL_LOGICAL="openai/gpt-4o-mini"
   export OPENROUTER_MODEL_COMPLETENESS="openai/gpt-4o-mini"
   ```

   Optional metadata headers:

   ```bash
   export OPENROUTER_APP_NAME="llm-output-arbitration-system"
   export OPENROUTER_SITE_URL="https://your-project-url.example"
   ```

4. Run the API:

   ```bash
   uvicorn app.main:app --reload
   ```

5. Open docs:

   - [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

## API Usage

`POST /arbitrate`

```json
{
  "prompt": "Explain why the sky appears blue.",
  "candidate_response": "The sky is blue because shorter wavelengths scatter more than longer wavelengths."
}
```

Response includes:

- Structured critiques per critic role
- Confidence score (0-1)
- Label (`pass`, `review`, `fail`)
- Final synthesized reasoning

If `OPENROUTER_API_KEY` is missing (or an upstream call fails), the service
automatically falls back to local heuristic critics.

`POST /arbitrate/trace`

Returns the same verdict plus per-critic execution metadata:

- model used
- source (`openrouter`, `fallback_no_key`, `fallback_error`)
- latency in ms
- fallback error (if any)

## UI (Streamlit)

Run the API first:

```bash
uvicorn app.main:app --reload
```

In another terminal, launch the UI:

```bash
streamlit run ui/streamlit_app.py
```

The UI lets you:

- submit prompt + candidate response
- choose `arbitrate` or `arbitrate/trace`
- inspect verdict, per-critic issues, and trace telemetry
- view raw JSON output for debugging

## Project Structure

- `app/main.py` - FastAPI app and routes.
- `app/arbitrator.py` - Orchestration + synthesis logic.
- `app/critics.py` - LLM-backed critics + heuristic fallback logic.
- `app/openrouter.py` - OpenRouter chat completions client.
- `app/config.py` - Environment-driven runtime settings.
- `app/schemas.py` - Typed request/response models.
- `app/storage.py` - SQLite persistence and audit logs.
- `tests/test_arbitrator.py` - Baseline behavior tests.
- `ui/streamlit_app.py` - Streamlit verdict explorer.

## Run Tests

```bash
pytest -q
```
