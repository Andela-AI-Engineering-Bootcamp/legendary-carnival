from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Integer, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from app.schemas import AnalyticsResponse, ArbitrationResponse


class Base(DeclarativeBase):
    pass


class ArbitrationLog(Base):
    __tablename__ = "arbitration_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    prompt: Mapped[str] = mapped_column(Text)
    candidate_response: Mapped[str] = mapped_column(Text)
    verdict_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Storage:
    def __init__(self, db_url: str = "sqlite:///./arbitration.db") -> None:
        self.engine = create_engine(db_url, future=True)
        Base.metadata.create_all(self.engine)

    def save(
        self,
        prompt: str,
        candidate_response: str,
        arbitration_response: ArbitrationResponse,
    ) -> None:
        payload = json.dumps(arbitration_response.model_dump(mode="json"))
        with Session(self.engine) as session:
            session.add(
                ArbitrationLog(
                    request_id=arbitration_response.request_id,
                    prompt=prompt,
                    candidate_response=candidate_response,
                    verdict_json=payload,
                )
            )
            session.commit()

    def get_by_request_id(self, request_id: str) -> dict[str, Any] | None:
        with Session(self.engine) as session:
            row = session.scalar(
                select(ArbitrationLog).where(ArbitrationLog.request_id == request_id)
            )
            if row is None:
                return None
            payload = json.loads(row.verdict_json)
            payload["prompt"] = row.prompt
            payload["candidate_response"] = row.candidate_response
            payload["created_at"] = row.created_at.isoformat()
            return payload

    def get_analytics(self) -> AnalyticsResponse:
        with Session(self.engine) as session:
            rows = list(session.scalars(select(ArbitrationLog)))

        total = len(rows)
        issues_by_critic: dict[str, int] = {}
        overruled_by_critic: dict[str, int] = {}
        failure_types: dict[str, int] = {}
        agreement_hits = 0
        agreement_total = 0

        for row in rows:
            payload = json.loads(row.verdict_json)
            verdict = payload.get("verdict", {})
            critiques = verdict.get("critiques", [])
            for critique in critiques:
                critic = critique.get("critic_name", "unknown")
                issue_count = len(critique.get("issues", []))
                issues_by_critic[critic] = issues_by_critic.get(critic, 0) + issue_count
                agreement_total += 1
                if issue_count == 0:
                    agreement_hits += 1
                for issue in critique.get("issues", []):
                    severity = issue.get("severity", "unknown")
                    failure_types[severity] = failure_types.get(severity, 0) + 1

            for dismissed in verdict.get("dismissed_flags", []):
                critic = dismissed.get("raised_by", "unknown")
                overruled_by_critic[critic] = overruled_by_critic.get(critic, 0) + 1

        agreement_rate = (agreement_hits / agreement_total) if agreement_total else 0.0
        return AnalyticsResponse(
            total_arbitrations=total,
            issues_by_critic=issues_by_critic,
            overruled_by_critic=overruled_by_critic,
            failure_types=failure_types,
            critic_agreement_rate=agreement_rate,
        )
