"""
계좌 및 API 자격증명 모델
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import DateTime, Enum as SQLEnum, ForeignKey, String, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.backend.core.database import Base

if TYPE_CHECKING:
    from .user import User
    from .trading import TradeRule, Order, Position
    from .logging import ExecutionLog


class BrokerType(str, Enum):
    """브로커 타입"""
    KIS = "KIS"  # 한국투자증권


class MarketType(str, Enum):
    """시장 타입"""
    US = "US"  # 미국
    KR = "KR"  # 한국


class AccountHealthStatus(str, Enum):
    """계좌 상태"""
    HEALTHY = "healthy"  # 정상
    WARNING = "warning"  # 경고
    ERROR = "error"  # 오류
    INACTIVE = "inactive"  # 비활성


class BrokerageAccount(Base):
    """
    증권 계좌 모델
    사용자의 증권사 계좌를 관리합니다.
    """
    
    __tablename__ = "brokerage_accounts"
    
    # 기본 키
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )
    
    # 외래 키
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # 계좌 정보
    nickname: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )
    broker: Mapped[BrokerType] = mapped_column(
        SQLEnum(BrokerType),
        default=BrokerType.KIS,
        nullable=False
    )
    market: Mapped[MarketType] = mapped_column(
        SQLEnum(MarketType),
        default=MarketType.US,
        nullable=False
    )
    
    # 상태
    enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )
    health_status: Mapped[AccountHealthStatus] = mapped_column(
        SQLEnum(AccountHealthStatus),
        default=AccountHealthStatus.INACTIVE,
        nullable=False
    )
    last_heartbeat: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    # 설정
    config: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="JSON 형식의 추가 설정"
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
    user: Mapped["User"] = relationship(
        "User",
        back_populates="brokerage_accounts"
    )
    api_credentials: Mapped[List["ApiCredential"]] = relationship(
        "ApiCredential",
        back_populates="account",
        cascade="all, delete-orphan"
    )
    trade_rules: Mapped[List["TradeRule"]] = relationship(
        "TradeRule",
        back_populates="account",
        cascade="all, delete-orphan"
    )
    orders: Mapped[List["Order"]] = relationship(
        "Order",
        back_populates="account",
        cascade="all, delete-orphan"
    )
    positions: Mapped[List["Position"]] = relationship(
        "Position",
        back_populates="account",
        cascade="all, delete-orphan"
    )
    execution_logs: Mapped[List["ExecutionLog"]] = relationship(
        "ExecutionLog",
        back_populates="account",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<BrokerageAccount(id={self.id}, nickname={self.nickname}, broker={self.broker})>"
    
    @property
    def is_healthy(self) -> bool:
        """정상 상태 여부"""
        return self.health_status == AccountHealthStatus.HEALTHY
    
    @property
    def is_active(self) -> bool:
        """활성 상태 여부"""
        return self.enabled and self.is_healthy


class ApiCredential(Base):
    """
    API 자격증명 모델
    증권사 API 접근을 위한 자격증명을 암호화하여 저장합니다.
    """
    
    __tablename__ = "api_credentials"
    
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
    
    # API 자격증명 (암호화 저장)
    app_key_encrypted: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="암호화된 App Key"
    )
    app_secret_encrypted: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="암호화된 App Secret"
    )
    account_no_encrypted: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="암호화된 계좌번호"
    )
    
    # 설정
    sandbox: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="모의투자 여부"
    )
    
    # 토큰 관리
    access_token_encrypted: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="암호화된 Access Token"
    )
    token_expire_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="토큰 만료 시각"
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
        back_populates="api_credentials"
    )
    
    def __repr__(self) -> str:
        return f"<ApiCredential(id={self.id}, account_id={self.account_id}, sandbox={self.sandbox})>"
    
    @property
    def is_token_valid(self) -> bool:
        """토큰 유효성 확인"""
        if not self.access_token_encrypted or not self.token_expire_at:
            return False
        return datetime.utcnow() < self.token_expire_at
