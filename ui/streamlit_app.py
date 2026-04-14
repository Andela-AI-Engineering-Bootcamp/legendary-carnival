from __future__ import annotations

import json
import sqlite3
from typing import Any

import httpx
import streamlit as st


DEFAULT_API_URL = "http://127.0.0.1:8000"


def _post_json(url: str, payload: dict[str, str]) -> dict[str, Any]:
    with httpx.Client(timeout=60.0) as client:
        response = client.post(url, json=payload)
        response.raise_for_status()
        return response.json()


@st.cache_data(ttl=5)
def _read_history(db_path: str, limit: int) -> list[dict[str, Any]]:
    query = (
        "SELECT request_id, prompt, candidate_response, verdict_json, created_at "
        "FROM arbitration_logs ORDER BY id DESC LIMIT ?"
    )
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(query, (limit,)).fetchall()

    records: list[dict[str, Any]] = []
    for row in rows:
        verdict_payload: dict[str, Any] = {}
        if row["verdict_json"]:
            try:
                verdict_payload = json.loads(row["verdict_json"])
            except json.JSONDecodeError:
                verdict_payload = {}
        records.append(
            {
                "request_id": row["request_id"],
                "prompt": row["prompt"] or "",
                "candidate_response": row["candidate_response"] or "",
                "created_at": row["created_at"] or "",
                "saved_payload": verdict_payload,
            }
        )
    return records


def _render_verdict(verdict: dict[str, Any]) -> None:
    c1, c2, c3 = st.columns(3)
    c1.metric("Label", str(verdict.get("label", "")))
    c2.metric("Confidence", f'{float(verdict.get("confidence", 0.0)):.2f}')
    c3.metric("Overall Score", f'{float(verdict.get("overall_score", 0.0)):.2f}')

    st.write(verdict.get("summary", ""))

    for critique in verdict.get("critiques", []):
        with st.expander(
            f'{critique.get("critic_name", "Critic")} ({critique.get("dimension", "")})'
        ):
            st.write(f'Score: {float(critique.get("score", 0.0)):.2f}')
            st.write(critique.get("rationale", ""))
            issues = critique.get("issues", [])
            if not issues:
                st.success("No issues flagged.")
            else:
                for issue in issues:
                    st.markdown(
                        f'- **{issue.get("severity", "low")}**: '
                        f'"{issue.get("quote", "")}" - {issue.get("description", "")}'
                    )


def _render_annotated_output(candidate_response: str, verdict: dict[str, Any]) -> None:
    st.subheader("Annotated Output")
    confirmed = verdict.get("confirmed_issues", [])
    dismissed = verdict.get("dismissed_flags", [])
    annotated = candidate_response

    for item in confirmed:
        issue = item.get("issue", "")
        if issue and issue in annotated:
            annotated = annotated.replace(
                issue,
                f"🔴[{issue}]",
                1,
            )
    for item in dismissed:
        issue = item.get("issue", "")
        if issue and issue in annotated:
            annotated = annotated.replace(
                issue,
                f"🟡[{issue}]",
                1,
            )

    st.markdown(
        "Legend: 🔴 confirmed issue | 🟡 dismissed/low-confidence flag | 🟢 validated claims"
    )
    st.write(annotated)


def _render_critic_comparison(verdict: dict[str, Any]) -> None:
    st.subheader("Critic Comparison")
    critiques = verdict.get("critiques", [])
    if not critiques:
        st.info("No critiques available.")
        return

    cols = st.columns(len(critiques))
    for col, critique in zip(cols, critiques):
        with col:
            st.markdown(f"**{critique.get('critic_name', 'Critic')}**")
            st.caption(f"Score: {float(critique.get('score', 0.0)):.2f}")
            issues = critique.get("issues", [])
            if issues:
                for issue in issues:
                    st.write(f"🟧 {issue.get('description', '')}")
            else:
                st.write("🟩 No issues")


def _render_traces(traces: list[dict[str, Any]]) -> None:
    if not traces:
        st.info("No traces returned.")
        return

    st.subheader("Critic Execution Trace")
    for trace in traces:
        cols = st.columns([2, 2, 2, 2, 3])
        cols[0].write(trace.get("critic_name", ""))
        cols[1].write(trace.get("model", ""))
        cols[2].write(trace.get("source", ""))
        cols[3].write(f'{float(trace.get("latency_ms", 0.0)):.2f} ms')
        cols[4].write(trace.get("error", "") or "-")


def main() -> None:
    st.set_page_config(page_title="LLM Arbitration Explorer", layout="wide")
    st.title("LLM Output Arbitration Explorer")

    if "prompt_value" not in st.session_state:
        st.session_state.prompt_value = "Explain why the sky appears blue."
    if "candidate_value" not in st.session_state:
        st.session_state.candidate_value = (
            "The sky appears blue because shorter wavelengths of sunlight "
            "scatter more strongly through the atmosphere than longer wavelengths."
        )

    with st.sidebar:
        st.header("Configuration")
        api_base_url = st.text_input("API Base URL", value=DEFAULT_API_URL).rstrip("/")
        use_trace = st.toggle("Use trace endpoint", value=True)
        use_v1 = st.toggle("Use v1 API routes", value=True)
        db_path = st.text_input("SQLite DB Path", value="arbitration.db")

        st.divider()
        st.subheader("History")
        history_limit = st.slider("Recent runs", min_value=5, max_value=50, value=15)
        history_options: dict[str, dict[str, Any]] = {}
        history = []
        try:
            history = _read_history(db_path=db_path, limit=history_limit)
        except sqlite3.Error as exc:
            st.caption(f"History unavailable: {exc}")

        if history:
            for item in history:
                label = (
                    f'{item["created_at"]} | {item["request_id"][:8]} | '
                    f'{item["prompt"][:45]}'
                )
                history_options[label] = item

            selected_label = st.selectbox(
                "Select a previous run",
                options=list(history_options.keys()),
            )
            if st.button("Load selected run", use_container_width=True):
                selected = history_options[selected_label]
                st.session_state.prompt_value = selected["prompt"]
                st.session_state.candidate_value = selected["candidate_response"]
                st.success("Loaded prompt/response from history.")
                st.rerun()
        else:
            st.caption("No saved runs yet.")

    prompt = st.text_area(
        "Prompt",
        value=st.session_state.prompt_value,
        height=140,
    )
    candidate_response = st.text_area(
        "Candidate Response",
        value=st.session_state.candidate_value,
        height=180,
    )

    st.subheader("Batch Mode")
    batch_inputs = st.text_area(
        "Batch Candidate Responses (one per line)",
        value="",
        height=120,
        placeholder="Paste multiple candidate responses, each on a new line.",
    )

    if st.button("Run Arbitration", type="primary"):
        if not prompt.strip() or not candidate_response.strip():
            st.error("Prompt and candidate response are required.")
            return

        if use_v1:
            endpoint = "/v1/arbitrate/trace" if use_trace else "/v1/arbitrate"
            if use_trace:
                endpoint = "/arbitrate/trace"
        else:
            endpoint = "/arbitrate/trace" if use_trace else "/arbitrate"
        url = f"{api_base_url}{endpoint}"
        payload = {"prompt": prompt, "candidate_response": candidate_response}
        st.session_state.prompt_value = prompt
        st.session_state.candidate_value = candidate_response

        try:
            with st.spinner("Evaluating response..."):
                result = _post_json(url, payload)
        except httpx.HTTPStatusError as exc:
            st.error(f"API error {exc.response.status_code}: {exc.response.text}")
            return
        except httpx.HTTPError as exc:
            st.error(f"Connection error: {exc}")
            return

        st.success(f'Request ID: {result.get("request_id", "")}')
        verdict = result.get("verdict", {})
        _render_annotated_output(candidate_response, verdict)
        _render_verdict(verdict)
        _render_critic_comparison(verdict)

        if use_trace:
            _render_traces(result.get("traces", []))

        with st.expander("Raw JSON"):
            st.code(json.dumps(result, indent=2), language="json")

    if st.button("Run Batch Arbitration"):
        lines = [line.strip() for line in batch_inputs.splitlines() if line.strip()]
        if not lines:
            st.error("Please provide at least one candidate response in batch input.")
            return

        batch_endpoint = "/v1/arbitrate/batch"
        batch_url = f"{api_base_url}{batch_endpoint}"
        batch_payload = {
            "items": [
                {"prompt": prompt, "candidate_response": line}
                for line in lines
            ]
        }
        try:
            with st.spinner("Running batch arbitration..."):
                batch_result = _post_json(batch_url, batch_payload)
        except httpx.HTTPStatusError as exc:
            st.error(f"API error {exc.response.status_code}: {exc.response.text}")
            return
        except httpx.HTTPError as exc:
            st.error(f"Connection error: {exc}")
            return

        rows = []
        for item in batch_result.get("results", []):
            verdict = item.get("verdict", {})
            rows.append(
                {
                    "request_id": item.get("request_id", ""),
                    "output_excerpt": item.get("verdict", {})
                    .get("critiques", [{}])[0]
                    .get("rationale", "")[:80],
                    "overall_score": verdict.get("overall_score", 0.0),
                    "overall_quality_score_10": verdict.get("overall_quality_score_10", 0.0),
                    "issue_count": len(verdict.get("confirmed_issues", [])),
                    "confidence": verdict.get("confidence", 0.0),
                }
            )
        st.subheader("Batch Results")
        st.dataframe(rows, use_container_width=True)


if __name__ == "__main__":
    main()
