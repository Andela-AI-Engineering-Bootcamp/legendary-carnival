from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from app.arbitrator import arbitrate_with_trace
from app.config import get_settings


ROOT = Path(__file__).resolve().parents[1]
CASES_PATH = ROOT / "test_cases" / "portfolio_cases.json"
OUT_DIR = ROOT / "artifacts" / "portfolio_cases"


def main() -> None:
    settings = get_settings()
    cases = json.loads(CASES_PATH.read_text())

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    out_json = OUT_DIR / f"portfolio_results_{timestamp}.json"
    out_md = OUT_DIR / f"portfolio_summary_{timestamp}.md"

    results = []
    for case in cases:
        result = arbitrate_with_trace(
            prompt=case["prompt"],
            candidate_response=case["candidate_response"],
            settings=settings,
        )
        results.append(
            {
                "case_id": case["id"],
                "title": case["title"],
                "notes": case["notes"],
                "result": result.model_dump(mode="json"),
            }
        )

    out_json.write_text(json.dumps(results, indent=2))

    md_lines = [
        "# Portfolio Case Results",
        "",
        f"Generated: {datetime.utcnow().isoformat()}Z",
        "",
    ]
    for item in results:
        verdict = item["result"]["verdict"]
        md_lines.extend(
            [
                f"## {item['title']} (`{item['case_id']}`)",
                f"- Notes: {item['notes']}",
                f"- Label: {verdict['label']}",
                f"- Quality score (1-10): {verdict['overall_quality_score_10']}",
                f"- Confidence: {verdict['confidence']} ({verdict['confidence_level']})",
                f"- Confirmed issues: {len(verdict.get('confirmed_issues', []))}",
                f"- Dismissed flags: {len(verdict.get('dismissed_flags', []))}",
                "",
            ]
        )

    out_md.write_text("\n".join(md_lines))
    print(f"Wrote JSON results to: {out_json}")
    print(f"Wrote markdown summary to: {out_md}")


if __name__ == "__main__":
    main()
