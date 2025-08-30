"""
트레이딩 관련 모델 (규칙, 주문, 포지션)
"""

import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Enum as SQLEnum, ForeignKey, String, Boolean, Text, Integer, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.backend.core.database import Base

if TYPE_CHECKING:
    from .account import BrokerageAccount
    from .logging import StrategySignal


class OrderSide(str, Enum):
    """주문 방향"""
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(str, Enum):
    """주문 상태"""
    PENDING = "pending"  # 대기중
    PLACED = "placed"  # 주문완료
    PARTIALLY_FILLED = "partially_filled"  # 부분체결
    FILLED = "filled"  # 전량체결
    CANCELLED = "cancelled"  # 취소됨
    REJECTED = "rejected"  # 거부됨
    FAILED = "failed"  # 실패


class TradeRule(Base):
    """
    트레이딩 규칙 모델
    자동매매 규칙과 조건을 정의합니다.
    """
    
    __tablename__ = "trade_rules"
    
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
    
    # 규칙 정보
    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False
    )
    symbol: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
        comment="종목코드 (예: AAPL)"
    )
    
    # 매매 조건
    buy_amount_usd: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="매수 금액 (USD)"
    )
    max_position: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="최대 포지션 금액 (USD)"
    )
    
    # 진입/청산 조건 (JSON/YAML)
    entry_condition: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="진입 조건 (JSON/YAML)"
    )
    exit_condition: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="청산 조건 (JSON/YAML)"
    )
    
    # 주문 설정
    time_in_force: Mapped[str] = mapped_column(
        String(10),
        default="IOC",
        nullable=False,
        comment="주문 유효기간 (IOC, FOK, GTD 등)"
    )
    cooldown_seconds: Mapped[int] = mapped_column(
        Integer,
        default=60,
        nullable=False,
        comment="재진입 쿨다운 (초)"
    )
    
    # 리스크 관리
    stop_loss_percent: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="손절 퍼센트"
    )
    take_profit_percent: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="익절 퍼센트"
    )
    
    # 상태
    enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )
    last_triggered_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    # 타임스탬프
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
    
    # 관계
    account: Mapped["BrokerageAccount"] = relationship(
        "BrokerageAccount",
        back_populates="trade_rules"
    )
    orders: Mapped[list["Order"]] = relationship(
        "Order",
        back_populates="rule",
        cascade="all, delete-orphan"
    )
    signals: Mapped[list["StrategySignal"]] = relationship(
        "StrategySignal",
        back_populates="rule",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<TradeRule(id={self.id}, name={self.name}, symbol={self.symbol})>"
    
    @property
    def is_in_cooldown(self) -> bool:
        """쿨다운 상태 확인"""
        if not self.last_triggered_at:
            return False
        elapsed = (datetime.utcnow() - self.last_triggered_at).total_seconds()
        return elapsed < self.cooldown_seconds


class Order(Base):
    """
    주문 모델
    실제 발생한 주문을 기록합니다.
    """
    
    __tablename__ = "orders"
    
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
    
    # 주문 정보
    symbol: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True
    )
    side: Mapped[OrderSide] = mapped_column(
        SQLEnum(OrderSide),
        nullable=False
    )
    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )
    price: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 4),
        nullable=True,
        comment="주문가격 (시장가는 NULL)"
    )
    
    # 상태
    status: Mapped[OrderStatus] = mapped_column(
        SQLEnum(OrderStatus),
        default=OrderStatus.PENDING,
        nullable=False,
        index=True
    )
    broker_order_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        unique=True,
        comment="브로커 주문번호"
    )
    
    # 체결 정보
    filled_quantity: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )
    avg_fill_price: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 4),
        nullable=True
    )
    commission: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(8, 4),
        nullable=True
    )
    
    # 원본 응답
    raw_response: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="브로커 API 원본 응답 (JSON)"
    )
    
    # 타임스탬프
    placed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    filled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
    
    # 관계
    account: Mapped["BrokerageAccount"] = relationship(
        "BrokerageAccount",
        back_populates="orders"
    )
    rule: Mapped[Optional["TradeRule"]] = relationship(
        "TradeRule",
        back_populates="orders"
    )
    
    def __repr__(self) -> str:
        return f"<Order(id={self.id}, symbol={self.symbol}, side={self.side}, status={self.status})>"
    
    @property
    def is_complete(self) -> bool:
        """주문 완료 여부"""
        return self.status in [OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED, OrderStatus.FAILED]
    
    @property
    def fill_rate(self) -> float:
        """체결률"""
        if self.quantity == 0:
            return 0.0
        return self.filled_quantity / self.quantity


class Position(Base):
    """
    포지션 모델
    현재 보유 중인 포지션을 관리합니다.
    """
    
    __tablename__ = "positions"
    
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
    
    # 포지션 정보
    symbol: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True
    )
    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )
    avg_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        nullable=False,
        comment="평균 매수가"
    )
    
    # 손익 정보
    current_price: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 4),
        nullable=True,
        comment="현재가"
    )
    unrealized_pnl: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        comment="미실현 손익"
    )
    unrealized_pnl_percent: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(8, 4),
        nullable=True,
        comment="미실현 손익률 (%)"
    )
    
    # 타임스탬프
    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
    
    # 관계
    account: Mapped["BrokerageAccount"] = relationship(
        "BrokerageAccount",
        back_populates="positions"
    )
    
    def __repr__(self) -> str:
        return f"<Position(id={self.id}, symbol={self.symbol}, quantity={self.quantity})>"
    
    @property
    def market_value(self) -> Decimal:
        """시장가치"""
        if self.current_price:
            return self.quantity * self.current_price
        return self.quantity * self.avg_price
    
    @property
    def cost_basis(self) -> Decimal:
        """매입원가"""
        return self.quantity * self.avg_price
