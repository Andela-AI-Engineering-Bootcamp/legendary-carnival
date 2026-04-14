from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from app.schemas import ArbitrationResponse


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
