"""
보안 관련 유틸리티
암호화, 해싱, JWT 토큰 관리 등을 담당합니다.
"""

import base64
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.backend.core.config import settings
from app.backend.core.logging import get_logger

logger = get_logger(__name__)

# 비밀번호 해싱 컨텍스트
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class EncryptionService:
    """
    AES-GCM을 사용한 데이터 암호화 서비스
    민감한 정보(API 키, 계좌번호 등)를 암호화하여 저장합니다.
    """
    
    def __init__(self, key: Optional[bytes] = None):
        """
        Args:
            key: 32바이트 암호화 키 (None이면 설정에서 로드)
        """
        if key is None:
            key = settings.encryption_key.get_secret_value().encode()[:32]
        
        # AES-256-GCM 암호화 객체 생성
        self.cipher = AESGCM(key)
    
    def encrypt(self, plaintext: str) -> str:
        """
        문자열을 암호화
        
        Args:
            plaintext: 암호화할 평문
        
        Returns:
            Base64 인코딩된 암호문 (nonce + ciphertext)
        """
        try:
            # 12바이트 nonce 생성
            nonce = os.urandom(12)
            
            # 평문을 바이트로 변환
            plaintext_bytes = plaintext.encode('utf-8')
            
            # 암호화
            ciphertext = self.cipher.encrypt(nonce, plaintext_bytes, None)
            
            # nonce와 암호문을 결합하여 Base64 인코딩
            encrypted = base64.b64encode(nonce + ciphertext).decode('utf-8')
            
            return encrypted
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise
    
    def decrypt(self, encrypted: str) -> str:
        """
        암호문을 복호화
        
        Args:
            encrypted: Base64 인코딩된 암호문
        
        Returns:
            복호화된 평문
        """
        try:
            # Base64 디코딩
            encrypted_bytes = base64.b64decode(encrypted.encode('utf-8'))
            
            # nonce와 암호문 분리
            nonce = encrypted_bytes[:12]
            ciphertext = encrypted_bytes[12:]
            
            # 복호화
            plaintext_bytes = self.cipher.decrypt(nonce, ciphertext, None)
            
            return plaintext_bytes.decode('utf-8')
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise


# 전역 암호화 서비스 인스턴스
encryption_service = EncryptionService()


def hash_password(password: str) -> str:
    """
    비밀번호를 해시화
    
    Args:
        password: 평문 비밀번호
    
    Returns:
        해시된 비밀번호
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    비밀번호 검증
    
    Args:
        plain_password: 평문 비밀번호
        hashed_password: 해시된 비밀번호
    
    Returns:
        비밀번호 일치 여부
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    subject: str,
    expires_delta: Optional[timedelta] = None,
    additional_claims: Optional[Dict[str, Any]] = None
) -> str:
    """
    JWT 액세스 토큰 생성
    
    Args:
        subject: 토큰 주체 (일반적으로 user_id)
        expires_delta: 만료 시간
        additional_claims: 추가 클레임
    
    Returns:
        JWT 토큰 문자열
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.jwt_expiration_minutes
        )
    
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "iat": datetime.now(timezone.utc),
        "type": "access"
    }
    
    if additional_claims:
        to_encode.update(additional_claims)
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm
    )
    
    return encoded_jwt


def decode_token(token: str) -> Dict[str, Any]:
    """
    JWT 토큰 디코딩 및 검증
    
    Args:
        token: JWT 토큰 문자열
    
    Returns:
        디코딩된 토큰 페이로드
    
    Raises:
        JWTError: 토큰이 유효하지 않은 경우
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key.get_secret_value(),
            algorithms=[settings.jwt_algorithm]
        )
        return payload
    except JWTError as e:
        logger.error(f"Token decode error: {e}")
        raise


def generate_api_key() -> str:
    """
    랜덤 API 키 생성
    
    Returns:
        32바이트 랜덤 문자열
    """
    return base64.urlsafe_b64encode(os.urandom(32)).decode('utf-8').rstrip('=')


def mask_sensitive_data(data: str, visible_chars: int = 4) -> str:
    """
    민감한 데이터 마스킹
    
    Args:
        data: 마스킹할 데이터
        visible_chars: 표시할 문자 수
    
    Returns:
        마스킹된 문자열
    
    Example:
        >>> mask_sensitive_data("1234567890", 4)
        "1234******"
    """
    if not data or len(data) <= visible_chars:
        return "*" * len(data) if data else ""
    
    return data[:visible_chars] + "*" * (len(data) - visible_chars)
