"""
인증 서비스
사용자 인증, 토큰 관리, 권한 검증 등을 처리합니다.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.backend.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    verify_token,
    validate_password_strength,
    generate_reset_token
)
from app.backend.models.user import User, UserRole
from app.backend.schemas.auth import UserCreate, UserLogin


class AuthService:
    """인증 서비스 클래스"""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
    
    async def register_user(self, user_data: UserCreate) -> User:
        """
        새 사용자를 등록합니다.
        
        Args:
            user_data: 사용자 등록 정보
            
        Returns:
            생성된 사용자 객체
            
        Raises:
            ValueError: 이메일이 이미 존재하는 경우
        """
        # 이메일 중복 확인
        existing_user = await self.get_user_by_email(user_data.email)
        if existing_user:
            raise ValueError("이미 등록된 이메일 주소입니다.")
        
        # 비밀번호 강도 검증
        password_check = validate_password_strength(user_data.password)
        if not password_check["valid"]:
            raise ValueError(f"비밀번호가 약합니다: {', '.join(password_check['errors'])}")
        
        # 새 사용자 생성
        hashed_password = get_password_hash(user_data.password)
        
        new_user = User(
            id=uuid.uuid4(),
            email=user_data.email,
            password_hash=hashed_password,
            name=user_data.name,
            role=user_data.role,
            is_active=True,
            is_verified=False,  # 이메일 인증 필요
            created_at=datetime.now(timezone.utc)
        )
        
        self.db.add(new_user)
        await self.db.commit()
        await self.db.refresh(new_user)
        
        return new_user
    
    async def authenticate_user(self, login_data: UserLogin) -> Optional[User]:
        """
        사용자 로그인을 인증합니다.
        
        Args:
            login_data: 로그인 정보
            
        Returns:
            인증된 사용자 객체 또는 None
        """
        user = await self.get_user_by_email(login_data.email)
        
        if not user:
            return None
        
        if not user.is_active:
            return None
        
        if not verify_password(login_data.password, user.password_hash):
            return None
        
        # 마지막 로그인 시간 업데이트
        user.last_login_at = datetime.now(timezone.utc)
        await self.db.commit()
        
        return user
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """
        이메일로 사용자를 조회합니다.
        
        Args:
            email: 사용자 이메일
            
        Returns:
            사용자 객체 또는 None
        """
        stmt = select(User).where(User.email == email)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_user_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        """
        ID로 사용자를 조회합니다.
        
        Args:
            user_id: 사용자 ID
            
        Returns:
            사용자 객체 또는 None
        """
        stmt = select(User).where(User.id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def update_user_password(self, user: User, current_password: str, new_password: str) -> bool:
        """
        사용자 비밀번호를 변경합니다.
        
        Args:
            user: 사용자 객체
            current_password: 현재 비밀번호
            new_password: 새 비밀번호
            
        Returns:
            비밀번호 변경 성공 여부
        """
        # 현재 비밀번호 확인
        if not verify_password(current_password, user.password_hash):
            return False
        
        # 새 비밀번호 강도 검증
        password_check = validate_password_strength(new_password)
        if not password_check["valid"]:
            raise ValueError(f"비밀번호가 약합니다: {', '.join(password_check['errors'])}")
        
        # 비밀번호 해시화 및 업데이트
        user.password_hash = get_password_hash(new_password)
        user.updated_at = datetime.now(timezone.utc)
        
        await self.db.commit()
        return True
    
    async def deactivate_user(self, user_id: uuid.UUID) -> bool:
        """
        사용자를 비활성화합니다.
        
        Args:
            user_id: 사용자 ID
            
        Returns:
            비활성화 성공 여부
        """
        user = await self.get_user_by_id(user_id)
        if not user:
            return False
        
        user.is_active = False
        user.updated_at = datetime.now(timezone.utc)
        
        await self.db.commit()
        return True
    
    async def verify_user_email(self, user_id: uuid.UUID) -> bool:
        """
        사용자 이메일을 인증합니다.
        
        Args:
            user_id: 사용자 ID
            
        Returns:
            인증 성공 여부
        """
        user = await self.get_user_by_id(user_id)
        if not user:
            return False
        
        user.is_verified = True
        user.updated_at = datetime.now(timezone.utc)
        
        await self.db.commit()
        return True
    
    def create_access_token_for_user(self, user: User) -> str:
        """
        사용자용 액세스 토큰을 생성합니다.
        
        Args:
            user: 사용자 객체
            
        Returns:
            JWT 액세스 토큰
        """
        token_data = {
            "sub": str(user.id),
            "email": user.email,
            "role": user.role.value,
            "name": user.name
        }
        return create_access_token(token_data)
    
    async def get_current_user_from_token(self, token: str) -> Optional[User]:
        """
        토큰에서 현재 사용자를 가져옵니다.
        
        Args:
            token: JWT 토큰
            
        Returns:
            사용자 객체 또는 None
        """
        payload = verify_token(token)
        if not payload:
            return None
        
        user_id = payload.get("sub")
        if not user_id:
            return None
        
        try:
            user_uuid = uuid.UUID(user_id)
            return await self.get_user_by_id(user_uuid)
        except ValueError:
            return None
    
    def check_user_permission(self, user: User, required_role: UserRole) -> bool:
        """
        사용자 권한을 확인합니다.
        
        Args:
            user: 사용자 객체
            required_role: 필요한 권한
            
        Returns:
            권한 확인 결과
        """
        if not user.is_active:
            return False
        
        # 관리자는 모든 권한을 가짐
        if user.role == UserRole.ADMIN:
            return True
        
        # 트레이더는 트레이더 권한과 뷰어 권한을 가짐
        if user.role == UserRole.TRADER and required_role in [UserRole.TRADER, UserRole.VIEWER]:
            return True
        
        # 뷰어는 뷰어 권한만 가짐
        if user.role == UserRole.VIEWER and required_role == UserRole.VIEWER:
            return True
        
        return False
