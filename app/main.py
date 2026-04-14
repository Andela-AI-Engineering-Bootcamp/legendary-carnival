from __future__ import annotations

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from app.arbitrator import arbitrate, arbitrate_with_trace
from app.config import get_settings
from app.rate_limit import InMemoryRateLimiter
from app.schemas import ArbitrationRequest, ArbitrationResponse, ArbitrationTraceResponse
from app.security import is_api_key_valid
from app.storage import Storage

app = FastAPI(title="LLM Output Arbitration System", version="0.1.0")
settings = get_settings()
storage = Storage(settings.database_url)
rate_limiter = InMemoryRateLimiter(
    requests=settings.rate_limit_requests,
    window_seconds=settings.rate_limit_window_seconds,
)

allow_all_origins = "*" in settings.cors_allow_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=not allow_all_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _require_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
    if not is_api_key_valid(x_api_key, settings.api_access_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key.",
        )


def _require_rate_limit(request: Request, response: Response) -> None:
    client_ip = request.client.host if request.client else "unknown"
    result = rate_limiter.consume(client_ip)
    response.headers["X-RateLimit-Limit"] = str(result.limit)
    response.headers["X-RateLimit-Remaining"] = str(result.remaining)
    response.headers["X-RateLimit-Window-Seconds"] = str(result.window_seconds)

    if not result.allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please retry later.",
            headers={
                "Retry-After": str(result.retry_after_seconds),
                "X-RateLimit-Limit": str(result.limit),
                "X-RateLimit-Remaining": str(result.remaining),
                "X-RateLimit-Window-Seconds": str(result.window_seconds),
            },
        )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
def root() -> HTMLResponse:
    html = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>AI Answer Quality Checker</title>
    <style>
      body { font-family: Arial, sans-serif; background: #0b1020; color: #e6e9ef; margin: 0; line-height: 1.45; }
      .wrap { max-width: 960px; margin: 24px auto; padding: 20px; }
      .card { background: #131a2f; border: 1px solid #2a355f; border-radius: 10px; padding: 16px; margin-bottom: 14px; }
      h1, h2 { margin-top: 0; }
      h1 { margin-bottom: 8px; }
      label { display: block; margin: 10px 0 6px; font-weight: 600; }
      input, textarea, select, button {
        width: 100%; box-sizing: border-box; border-radius: 8px; border: 1px solid #405080;
        background: #0f1529; color: #e6e9ef; padding: 10px;
      }
      .small { font-size: 13px; color: #b6c0e0; }
      textarea { min-height: 120px; resize: vertical; }
      button { background: #5167ff; border: none; font-weight: 700; cursor: pointer; margin-top: 12px; }
      button:hover { background: #6779ff; }
      .row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
      .muted { color: #a6b0cf; font-size: 14px; }
      pre {
        background: #0a1022; color: #d8e1ff; border: 1px solid #27345f;
        border-radius: 8px; padding: 12px; overflow: auto; max-height: 400px;
      }
      .chips { display: flex; gap: 8px; flex-wrap: wrap; margin: 8px 0 0; }
      .chip { border: 1px solid #405080; background: #111938; color: #d7deff; padding: 6px 10px; border-radius: 999px; cursor: pointer; font-size: 13px; }
      .chip:hover { background: #172148; }
      .metrics { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin: 8px 0 14px; }
      .metric { background: #0d1531; border: 1px solid #2f3d6b; border-radius: 8px; padding: 10px; }
      .metric .k { font-size: 12px; color: #aeb9dd; }
      .metric .v { font-size: 18px; font-weight: 700; margin-top: 4px; }
      .badge { display: inline-block; padding: 4px 8px; border-radius: 6px; font-size: 12px; font-weight: 700; }
      .pass { background: #133924; color: #95f6bc; }
      .review { background: #3f3513; color: #ffe28a; }
      .fail { background: #451a1a; color: #ffb0b0; }
      .issues { margin-top: 6px; }
      .issues li { margin-bottom: 6px; }
      .hidden { display: none; }
      a { color: #9ab0ff; }
      @media (max-width: 700px) { .row { grid-template-columns: 1fr; } }
    </style>
  </head>
  <body>
    <div class="wrap">
      <div class="card">
        <h1>AI Answer Quality Checker</h1>
        <p class="muted">
          Paste a prompt and an AI answer to get a quality verdict in plain terms.
          You can still use
          <a href="/docs" target="_blank" rel="noreferrer">Swagger Docs</a>.
        </p>
      </div>

      <div class="card">
        <h2>1) Your Input</h2>
        <div class="row">
          <div>
            <label for="apiKey">Access Key (if required)</label>
            <input id="apiKey" type="password" placeholder="Paste API key" />
            <div class="small">If your admin enabled API protection, paste your key here.</div>
          </div>
          <div>
            <label for="endpoint">Analysis Mode</label>
            <select id="endpoint">
              <option value="/arbitrate">Standard (faster)</option>
              <option value="/arbitrate/trace">Advanced (includes technical trace)</option>
            </select>
          </div>
        </div>

        <div class="chips">
          <button class="chip" id="exampleGood" type="button">Load good example</button>
          <button class="chip" id="exampleWeak" type="button">Load weak example</button>
        </div>

        <label for="prompt">Prompt</label>
        <textarea id="prompt">Explain why the sky appears blue.</textarea>

        <label for="candidate">AI Candidate Response</label>
        <textarea id="candidate">The sky appears blue because shorter wavelengths of sunlight scatter more strongly in Earth's atmosphere.</textarea>

        <button id="runBtn">Check Answer Quality</button>
      </div>

      <div class="card">
        <h2>2) Result</h2>
        <div id="summary" class="muted">No analysis yet.</div>
        <div id="verdictPanel" class="hidden">
          <div class="metrics">
            <div class="metric"><div class="k">Verdict</div><div class="v" id="metricLabel">-</div></div>
            <div class="metric"><div class="k">Confidence</div><div class="v" id="metricConfidence">-</div></div>
            <div class="metric"><div class="k">Overall Score</div><div class="v" id="metricScore">-</div></div>
          </div>
          <div id="criticBreakdown"></div>
        </div>
        <button id="toggleRawBtn" type="button">Show Raw JSON</button>
        <pre id="result" class="hidden">No request sent yet.</pre>
      </div>
    </div>

    <script>
      const runBtn = document.getElementById("runBtn");
      const toggleRawBtn = document.getElementById("toggleRawBtn");
      const result = document.getElementById("result");
      const verdictPanel = document.getElementById("verdictPanel");
      const summary = document.getElementById("summary");
      const metricLabel = document.getElementById("metricLabel");
      const metricConfidence = document.getElementById("metricConfidence");
      const metricScore = document.getElementById("metricScore");
      const criticBreakdown = document.getElementById("criticBreakdown");
      const endpointSelect = document.getElementById("endpoint");

      function escapeHtml(str) {
        return String(str)
          .replaceAll("&", "&amp;")
          .replaceAll("<", "&lt;")
          .replaceAll(">", "&gt;");
      }

      function renderVerdict(body) {
        const verdict = body?.verdict || {};
        const label = verdict.label || "unknown";
        metricLabel.innerHTML = `<span class="badge ${label}">${label.toUpperCase()}</span>`;
        metricConfidence.textContent = typeof verdict.confidence === "number" ? verdict.confidence.toFixed(2) : "-";
        metricScore.textContent = typeof verdict.overall_score === "number" ? verdict.overall_score.toFixed(2) : "-";
        summary.textContent = verdict.summary || "Analysis completed.";

        const critiques = Array.isArray(verdict.critiques) ? verdict.critiques : [];
        criticBreakdown.innerHTML = critiques.map((c) => {
          const issues = Array.isArray(c.issues) ? c.issues : [];
          const issuesHtml = issues.length
            ? `<ul class="issues">${issues.map((i) => `<li><strong>${escapeHtml(i.severity || "low")}:</strong> ${escapeHtml(i.description || "")}</li>`).join("")}</ul>`
            : `<div class="small">No issues flagged.</div>`;
          return `
            <div class="card" style="margin-top:10px;">
              <div><strong>${escapeHtml(c.critic_name || "Critic")}</strong></div>
              <div class="small">Score: ${typeof c.score === "number" ? c.score.toFixed(2) : "-"}</div>
              <div class="small">${escapeHtml(c.rationale || "")}</div>
              ${issuesHtml}
            </div>
          `;
        }).join("");

        verdictPanel.classList.remove("hidden");
      }

      document.getElementById("exampleGood").addEventListener("click", () => {
        document.getElementById("prompt").value = "Explain why the sky appears blue.";
        document.getElementById("candidate").value = "The sky appears blue because Earth's atmosphere scatters shorter blue wavelengths of sunlight more than longer red wavelengths, making blue light more visible from most viewing angles.";
      });

      document.getElementById("exampleWeak").addEventListener("click", () => {
        document.getElementById("prompt").value = "Explain why the sky appears blue.";
        document.getElementById("candidate").value = "The sky is always blue because oceans reflect into the sky. That's all.";
      });

      toggleRawBtn.addEventListener("click", () => {
        const hidden = result.classList.contains("hidden");
        result.classList.toggle("hidden");
        toggleRawBtn.textContent = hidden ? "Hide Raw JSON" : "Show Raw JSON";
      });

      runBtn.addEventListener("click", async () => {
        const prompt = document.getElementById("prompt").value.trim();
        const candidate = document.getElementById("candidate").value.trim();
        const endpoint = endpointSelect.value === "Advanced (includes technical trace)" ? "/arbitrate/trace" : endpointSelect.value;
        const apiKey = document.getElementById("apiKey").value.trim();

        if (!prompt || !candidate) {
          summary.textContent = "Prompt and AI Candidate Response are required.";
          return;
        }

        const headers = { "Content-Type": "application/json" };
        if (apiKey) headers["X-API-Key"] = apiKey;

        summary.textContent = "Analyzing...";
        verdictPanel.classList.add("hidden");
        try {
          const resp = await fetch(endpoint, {
            method: "POST",
            headers,
            body: JSON.stringify({
              prompt: prompt,
              candidate_response: candidate
            })
          });

          const data = await resp.json();
          const payload = {
            status: resp.status,
            headers: {
              "x-ratelimit-limit": resp.headers.get("x-ratelimit-limit"),
              "x-ratelimit-remaining": resp.headers.get("x-ratelimit-remaining"),
              "retry-after": resp.headers.get("retry-after")
            },
            body: data
          };
          result.textContent = JSON.stringify(payload, null, 2);

          if (resp.ok) {
            renderVerdict(data);
          } else {
            summary.textContent = "Request failed. Check API key or inputs.";
          }
        } catch (err) {
          summary.textContent = "Request failed: " + String(err);
        }
      });
    </script>
  </body>
</html>
"""
    return HTMLResponse(content=html)


@app.post(
    "/arbitrate",
    response_model=ArbitrationResponse,
    dependencies=[Depends(_require_api_key), Depends(_require_rate_limit)],
)
def run_arbitration(request: ArbitrationRequest) -> ArbitrationResponse:
    result = arbitrate(
        prompt=request.prompt,
        candidate_response=request.candidate_response,
        settings=settings,
    )
    storage.save(
        prompt=request.prompt,
        candidate_response=request.candidate_response,
        arbitration_response=result,
    )
    return result


@app.post(
    "/arbitrate/trace",
    response_model=ArbitrationTraceResponse,
    dependencies=[Depends(_require_api_key), Depends(_require_rate_limit)],
)
def run_arbitration_with_trace(request: ArbitrationRequest) -> ArbitrationTraceResponse:
    result = arbitrate_with_trace(
        prompt=request.prompt,
        candidate_response=request.candidate_response,
        settings=settings,
    )
    storage.save(
        prompt=request.prompt,
        candidate_response=request.candidate_response,
        arbitration_response=ArbitrationResponse(
            request_id=result.request_id,
            verdict=result.verdict,
        ),
    )
    return result
