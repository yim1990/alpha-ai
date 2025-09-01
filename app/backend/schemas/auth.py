"""
인증 관련 Pydantic 스키마
요청/응답 데이터 검증과 API 문서화를 위한 스키마들을 정의합니다.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.backend.models.user import UserRole


class UserBase(BaseModel):
    """사용자 기본 스키마"""
    
    email: EmailStr = Field(..., description="이메일 주소")
    name: str = Field(..., min_length=2, max_length=100, description="사용자 이름")


class UserCreate(UserBase):
    """사용자 생성 스키마"""
    
    password: str = Field(..., min_length=8, max_length=128, description="비밀번호")
    role: UserRole = Field(default=UserRole.VIEWER, description="사용자 역할")
    
    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """비밀번호 형식 검증 (간소화된 규칙)"""
        if len(v) < 8:
            raise ValueError("비밀번호는 최소 8자 이상이어야 합니다.")
        if not any(c.islower() for c in v):
            raise ValueError("비밀번호에 소문자가 포함되어야 합니다.")
        if not any(c.isdigit() for c in v):
            raise ValueError("비밀번호에 숫자가 포함되어야 합니다.")
        return v


class UserLogin(BaseModel):
    """로그인 스키마"""
    
    email: EmailStr = Field(..., description="이메일 주소")
    password: str = Field(..., description="비밀번호")


class UserUpdate(BaseModel):
    """사용자 정보 수정 스키마"""
    
    name: Optional[str] = Field(None, min_length=2, max_length=100, description="사용자 이름")
    role: Optional[UserRole] = Field(None, description="사용자 역할")
    is_active: Optional[bool] = Field(None, description="활성 상태")


class PasswordChange(BaseModel):
    """비밀번호 변경 스키마"""
    
    current_password: str = Field(..., description="현재 비밀번호")
    new_password: str = Field(..., min_length=8, max_length=128, description="새 비밀번호")
    
    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        """새 비밀번호 형식 검증 (간소화된 규칙)"""
        if len(v) < 8:
            raise ValueError("비밀번호는 최소 8자 이상이어야 합니다.")
        if not any(c.islower() for c in v):
            raise ValueError("비밀번호에 소문자가 포함되어야 합니다.")
        if not any(c.isdigit() for c in v):
            raise ValueError("비밀번호에 숫자가 포함되어야 합니다.")
        return v


class PasswordReset(BaseModel):
    """비밀번호 재설정 스키마"""
    
    email: EmailStr = Field(..., description="이메일 주소")


class PasswordResetConfirm(BaseModel):
    """비밀번호 재설정 확인 스키마"""
    
    token: str = Field(..., description="재설정 토큰")
    new_password: str = Field(..., min_length=8, max_length=128, description="새 비밀번호")


class UserResponse(UserBase):
    """사용자 응답 스키마"""
    
    id: UUID = Field(..., description="사용자 ID")
    role: UserRole = Field(..., description="사용자 역할")
    is_active: bool = Field(..., description="활성 상태")
    is_verified: bool = Field(..., description="인증 상태")
    created_at: datetime = Field(..., description="생성 시간")
    last_login_at: Optional[datetime] = Field(None, description="마지막 로그인 시간")
    
    class Config:
        from_attributes = True


class Token(BaseModel):
    """토큰 응답 스키마"""
    
    access_token: str = Field(..., description="액세스 토큰")
    token_type: str = Field(default="bearer", description="토큰 타입")
    expires_in: int = Field(..., description="토큰 만료 시간 (초)")


class TokenData(BaseModel):
    """토큰 데이터 스키마"""
    
    user_id: Optional[UUID] = None
    email: Optional[str] = None


class LoginResponse(BaseModel):
    """로그인 응답 스키마"""
    
    user: UserResponse = Field(..., description="사용자 정보")
    token: Token = Field(..., description="인증 토큰")


class PasswordStrengthCheck(BaseModel):
    """비밀번호 강도 확인 요청 스키마"""
    
    password: str = Field(..., description="확인할 비밀번호")


class PasswordStrengthResult(BaseModel):
    """비밀번호 강도 확인 결과 스키마"""
    
    valid: bool = Field(..., description="유효한 비밀번호 여부")
    score: int = Field(..., ge=0, le=5, description="비밀번호 강도 점수 (0-5)")
    errors: list[str] = Field(..., description="오류 메시지 목록")


class ApiResponse(BaseModel):
    """공통 API 응답 스키마"""
    
    success: bool = Field(..., description="요청 성공 여부")
    message: str = Field(..., description="응답 메시지")
    data: Optional[dict] = Field(None, description="응답 데이터")


class ErrorResponse(BaseModel):
    """에러 응답 스키마"""
    
    error: str = Field(..., description="에러 타입")
    message: str = Field(..., description="에러 메시지")
    details: Optional[dict] = Field(None, description="에러 상세 정보")
