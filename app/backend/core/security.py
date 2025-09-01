"""
보안 관련 유틸리티
비밀번호 해싱, JWT 토큰 생성/검증, 암호화 등을 처리합니다.
"""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Union

import bcrypt
from jose import JWTError, jwt
from passlib.context import CryptContext

from .config import settings


# 비밀번호 해싱을 위한 컨텍스트 (bcrypt 호환성 문제 해결)
pwd_context = CryptContext(
    schemes=["bcrypt"], 
    deprecated="auto",
    bcrypt__rounds=12,  # bcrypt 라운드 설정
    bcrypt__ident="2b"  # bcrypt 식별자 명시적 설정
)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    평문 비밀번호와 해시된 비밀번호를 비교합니다.
    
    Args:
        plain_password: 평문 비밀번호
        hashed_password: 해시된 비밀번호
        
    Returns:
        비밀번호 일치 여부
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    비밀번호를 해시화합니다.
    
    Args:
        password: 평문 비밀번호
        
    Returns:
        해시된 비밀번호
    """
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Union[timedelta, None] = None) -> str:
    """
    JWT 액세스 토큰을 생성합니다.
    
    Args:
        data: 토큰에 포함할 데이터
        expires_delta: 토큰 만료 시간 (기본: 7일)
        
    Returns:
        JWT 토큰 문자열
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expiration_minutes)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.jwt_secret_key.get_secret_value(), 
        algorithm=settings.jwt_algorithm
    )
    return encoded_jwt


def verify_token(token: str) -> Union[dict, None]:
    """
    JWT 토큰을 검증하고 페이로드를 반환합니다.
    
    Args:
        token: JWT 토큰
        
    Returns:
        토큰 페이로드 또는 None (검증 실패 시)
    """
    try:
        payload = jwt.decode(
            token, 
            settings.jwt_secret_key.get_secret_value(), 
            algorithms=[settings.jwt_algorithm]
        )
        return payload
    except JWTError:
        return None


def generate_reset_token() -> str:
    """
    비밀번호 재설정용 랜덤 토큰을 생성합니다.
    
    Returns:
        32바이트 랜덤 토큰 (hex 문자열)
    """
    return secrets.token_hex(32)


def validate_password_strength(password: str) -> dict[str, Any]:
    """
    비밀번호 강도를 검증합니다.
    
    Args:
        password: 검증할 비밀번호
        
    Returns:
        검증 결과 딕셔너리
    """
    errors = []
    
    # 최소 길이 검사
    if len(password) < 8:
        errors.append("비밀번호는 최소 8자 이상이어야 합니다.")
    

    # 소문자 포함 검사
    if not any(c.islower() for c in password):
        errors.append("비밀번호에 소문자가 포함되어야 합니다.")
    
    # 숫자 포함 검사
    if not any(c.isdigit() for c in password):
        errors.append("비밀번호에 숫자가 포함되어야 합니다.")
    

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "score": max(0, 3 - len(errors))  # 0-3점 스코어 (대문자/특수문자 검사 제거로 최대값 조정)
    }


def generate_api_key() -> str:
    """
    API 키를 생성합니다.
    
    Returns:
        64바이트 랜덤 API 키 (hex 문자열)
    """
    return secrets.token_hex(64)


class TokenData:
    """JWT 토큰 데이터 클래스"""
    
    def __init__(self, user_id: str = None, email: str = None):
        self.user_id = user_id
        self.email = email