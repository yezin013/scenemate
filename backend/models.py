"""DB 테이블을 파이썬 객체로 매핑 (SQLAlchemy 모델)."""
from sqlalchemy import Column, BigInteger, Text, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
try:
    from pgvector.sqlalchemy import Vector
    _VECTOR_TYPE = Vector(768)
except ImportError:
    from sqlalchemy import Text
    _VECTOR_TYPE = Text()  # pgvector 없을 때 폴백 (임베딩 기능 비활성)

from db import Base


class Analysis(Base):
    """대사 분석 — analysis 테이블."""
    __tablename__ = "analysis"

    id = Column(BigInteger, primary_key=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    script_id = Column(BigInteger, nullable=False)
    user_id = Column(PGUUID(as_uuid=False))
    subtext = Column(Text)
    action_verb = Column(Text)
    emotion_arc = Column(Text)
    context = Column(Text)
    character_bg = Column(Text)
    relationship = Column(Text)
    real_goal = Column(Text)
    ai_analysis = Column(JSONB)


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
    user_id = Column(PGUUID(as_uuid=False))               # Supabase Auth 사용자 UUID
    embedding = Column(_VECTOR_TYPE, nullable=True)         # 유사도 검색용 임베딩
