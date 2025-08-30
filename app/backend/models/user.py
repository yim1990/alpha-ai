"""
사용자 모델
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, List

from sqlalchemy import DateTime, Enum as SQLEnum, String, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.backend.core.database import Base

if TYPE_CHECKING:
    from .account import BrokerageAccount


class UserRole(str, Enum):
    """사용자 역할"""
    ADMIN = "admin"  # 전체 관리자
    TRADER = "trader"  # 트레이더
    VIEWER = "viewer"  # 조회만 가능


class User(Base):
    """
    사용자 모델
    시스템에 접근하는 사용자를 관리합니다.
    """
    
    __tablename__ = "users"
    
    # 기본 키
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )
    
    # 인증 정보
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    
    # 프로필
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )
    role: Mapped[UserRole] = mapped_column(
        SQLEnum(UserRole),
        default=UserRole.VIEWER,
        nullable=False
    )
    
    # 상태
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
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
    last_login_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    # 관계
    brokerage_accounts: Mapped[List["BrokerageAccount"]] = relationship(
        "BrokerageAccount",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"
    
    @property
    def is_admin(self) -> bool:
        """관리자 여부"""
        return self.role == UserRole.ADMIN
    
    @property
    def can_trade(self) -> bool:
        """거래 권한 여부"""
        return self.role in [UserRole.ADMIN, UserRole.TRADER]
