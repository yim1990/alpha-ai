"""
로깅 및 시그널 관련 모델
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Enum as SQLEnum, ForeignKey, String, Text, Numeric, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.backend.core.database import Base

if TYPE_CHECKING:
    from .account import BrokerageAccount
    from .trading import TradeRule


class LogLevel(str, Enum):
    """로그 레벨"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class SignalType(str, Enum):
    """시그널 타입"""
    ENTRY = "ENTRY"  # 진입 시그널
    EXIT = "EXIT"  # 청산 시그널
    HOLD = "HOLD"  # 보유 유지
    NEUTRAL = "NEUTRAL"  # 중립


class ExecutionLog(Base):
    """
    실행 로그 모델
    시스템 실행 중 발생하는 모든 로그를 기록합니다.
    """
    
    __tablename__ = "execution_logs"
    
    # 기본 키
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )
    
    # 외래 키
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("brokerage_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    rule_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("trade_rules.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # 로그 정보
    level: Mapped[LogLevel] = mapped_column(
        SQLEnum(LogLevel),
        default=LogLevel.INFO,
        nullable=False,
        index=True
    )
    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="로그 카테고리 (order, position, auth, etc)"
    )
    message: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    
    # 컨텍스트 데이터
    context: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="추가 컨텍스트 데이터 (JSON)"
    )
    
    # 에러 정보
    error_code: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        index=True
    )
    error_details: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    
    # 타임스탬프
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
        index=True
    )
    
    # 관계
    account: Mapped["BrokerageAccount"] = relationship(
        "BrokerageAccount",
        back_populates="execution_logs"
    )
    rule: Mapped[Optional["TradeRule"]] = relationship(
        "TradeRule"
    )
    
    def __repr__(self) -> str:
        return f"<ExecutionLog(id={self.id}, level={self.level}, category={self.category})>"
    
    @property
    def is_error(self) -> bool:
        """에러 로그 여부"""
        return self.level in [LogLevel.ERROR, LogLevel.CRITICAL]


class StrategySignal(Base):
    """
    전략 시그널 모델
    트레이딩 전략에서 생성된 시그널을 기록합니다.
    """
    
    __tablename__ = "strategy_signals"
    
    # 기본 키
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )
    
    # 외래 키
    rule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("trade_rules.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # 시그널 정보
    signal_type: Mapped[SignalType] = mapped_column(
        SQLEnum(SignalType),
        nullable=False,
        index=True
    )
    symbol: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True
    )
    
    # 시그널 강도 및 스코어
    score: Mapped[Optional[float]] = mapped_column(
        Numeric(5, 4),
        nullable=True,
        comment="시그널 강도 (0.0 ~ 1.0)"
    )
    confidence: Mapped[Optional[float]] = mapped_column(
        Numeric(5, 4),
        nullable=True,
        comment="신뢰도 (0.0 ~ 1.0)"
    )
    
    # 시그널 데이터
    payload: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="시그널 상세 데이터 (JSON)"
    )
    
    # 실행 정보
    executed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="시그널 실행 여부"
    )
    executed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    execution_result: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="실행 결과 (JSON)"
    )
    
    # 타임스탬프
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
        index=True
    )
    
    # 관계
    rule: Mapped["TradeRule"] = relationship(
        "TradeRule",
        back_populates="signals"
    )
    
    def __repr__(self) -> str:
        return f"<StrategySignal(id={self.id}, type={self.signal_type}, symbol={self.symbol})>"
    
    @property
    def is_actionable(self) -> bool:
        """실행 가능한 시그널 여부"""
        return self.signal_type in [SignalType.ENTRY, SignalType.EXIT] and not self.executed
