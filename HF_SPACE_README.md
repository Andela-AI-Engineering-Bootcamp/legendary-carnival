---
title: LLM Output Arbitration API
short_description: Multi-critic quality gate API that scores AI answers for factuality, logic, and completeness.
emoji: "🧠"
colorFrom: indigo
colorTo: blue
sdk: docker
pinned: false
---

# LLM Output Arbitration API

Public FastAPI service for evaluating LLM responses with multi-critic arbitration.

## Endpoints

- `GET /health`
- `POST /arbitrate`
- `POST /arbitrate/trace`
- Interactive docs at `/docs`

## Required Space Secrets / Variables

- `OPENROUTER_API_KEY` (secret)
- `OPENROUTER_BASE_URL` (optional, default: `https://openrouter.ai/api/v1`)
- `OPENROUTER_APP_NAME` (optional)
- `OPENROUTER_SITE_URL` (optional)
- `OPENROUTER_MODEL_FACTUAL` (optional)
- `OPENROUTER_MODEL_LOGICAL` (optional)
- `OPENROUTER_MODEL_COMPLETENESS` (optional)
- `CORS_ALLOW_ORIGINS` (optional, default: `*`)
- `DATABASE_URL` (optional, for persistent storage use `sqlite:////data/arbitration.db`)
- `API_ACCESS_KEY` (optional but recommended for public deployments)
- `RATE_LIMIT_REQUESTS` (optional, default: `0` = disabled)
- `RATE_LIMIT_WINDOW_SECONDS` (optional, default: `60`)

When enabled, arbitration endpoints include rate-limit headers and return
`Retry-After` on `429` responses.
