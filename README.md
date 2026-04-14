# Project 5: LLM Output Arbitration System

Multi-agent arbitration pipeline that critiques a candidate LLM response with
specialized evaluators, then synthesizes those critiques into a confidence-based
verdict.

## What This MVP Includes

- FastAPI service with a production-style API shape.
- Three critic roles:
  - Factual Accuracy Critic
  - Logical Consistency Critic
  - Completeness Critic
- Strict, typed output models using Pydantic.
- SQLite + SQLAlchemy audit logging of requests and final verdicts.
- Deterministic baseline heuristics so the system runs without provider keys.

## Tech Stack

- Python 3.11+
- FastAPI
- Pydantic v2
- SQLAlchemy
- pytest

The architecture is intentionally provider-agnostic so real LLM providers
(OpenAI/Anthropic/Ollama) can be integrated behind the critic interfaces.

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

3. Run the API:

   ```bash
   uvicorn app.main:app --reload
   ```

4. Open docs:

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

## Project Structure

- `app/main.py` - FastAPI app and routes.
- `app/arbitrator.py` - Orchestration + synthesis logic.
- `app/critics.py` - Independent critic evaluators.
- `app/schemas.py` - Typed request/response models.
- `app/storage.py` - SQLite persistence and audit logs.
- `tests/test_arbitrator.py` - Baseline behavior tests.

## Run Tests

```bash
pytest -q
```