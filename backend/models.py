"""DB 테이블을 파이썬 객체로 매핑 (SQLAlchemy 모델)."""
from sqlalchemy import Column, BigInteger, Text, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB

from db import Base


class Script(Base):
    """대사 아카이브 — scripts 테이블."""
    __tablename__ = "scripts"

    id = Column(BigInteger, primary_key=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    source = Column(Text, nullable=False, default="ai")   # 'ai' | 'manual'
    track = Column(Text)                                   # 'appearance' | 'personality'
    title = Column(Text)
    setup = Column(Text)
    script_text = Column(Text, nullable=False)
    fit_reason = Column(Text)
    inputs = Column(JSONB)                                 # {외모키워드, 자기소개, 말투}
    feedback = Column(JSONB)                               # 오디션 피드백 누적 배열 [{date, venue, result, memo, created_at}]
