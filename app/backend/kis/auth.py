"""
KIS API 인증 서비스
Access Token 발급 및 갱신을 담당합니다.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
from pydantic import BaseModel, Field
from tenacity import retry, stop_after_attempt, wait_exponential

from app.backend.core.config import settings
from app.backend.core.logging import get_logger, log_context

logger = get_logger(__name__)


class AccessToken(BaseModel):
    """KIS Access Token 모델"""
    
    access_token: str = Field(..., description="액세스 토큰")
    token_type: str = Field(default="Bearer", description="토큰 타입")
    expires_in: int = Field(..., description="만료 시간(초)")
    expires_at: datetime = Field(..., description="만료 시각")
    
    @property
    def is_expired(self) -> bool:
        """토큰 만료 여부 확인"""
        # 5분 여유를 두고 만료 체크
        buffer = timedelta(minutes=5)
        return datetime.now(timezone.utc) >= (self.expires_at - buffer)
    
    @property
    def authorization_header(self) -> str:
        """Authorization 헤더 값"""
        return f"{self.token_type} {self.access_token}"


class KISAuthService:
    """
    KIS API 인증 서비스
    토큰 발급, 갱신, 관리를 담당합니다.
    """
    
    def __init__(
        self,
        app_key: Optional[str] = None,
        app_secret: Optional[str] = None,
        use_sandbox: Optional[bool] = None
    ):
        """
        Args:
            app_key: KIS API App Key
            app_secret: KIS API App Secret  
            use_sandbox: 모의투자 사용 여부
        """
        self.app_key = app_key or settings.kis_app_key.get_secret_value()
        self.app_secret = app_secret or settings.kis_app_secret.get_secret_value()
        self.use_sandbox = use_sandbox if use_sandbox is not None else settings.kis_use_sandbox
        self.base_url = settings.kis_base_url
        
        # 현재 토큰 캐시
        self._current_token: Optional[AccessToken] = None
        self._token_lock = asyncio.Lock()
        
        # HTTP 클라이언트
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(30.0),
            headers={
                "content-type": "application/json; charset=utf-8",
                "User-Agent": "AlphaAI/1.0"
            }
        )
    
    async def __aenter__(self):
        """비동기 컨텍스트 매니저 진입"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """비동기 컨텍스트 매니저 종료"""
        await self.close()
    
    async def close(self):
        """HTTP 클라이언트 종료"""
        await self._client.aclose()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def get_access_token(self, force_refresh: bool = False) -> AccessToken:
        """
        Access Token 발급
        
        Args:
            force_refresh: 강제 재발급 여부
        
        Returns:
            AccessToken 객체
        
        Raises:
            httpx.HTTPError: API 요청 실패
        """
        async with self._token_lock:
            # 캐시된 토큰이 유효하면 반환
            if not force_refresh and self._current_token and not self._current_token.is_expired:
                logger.debug("Using cached access token")
                return self._current_token
            
            logger.info("Requesting new access token", extra=log_context(
                sandbox=self.use_sandbox
            ))
            
            # 토큰 발급 요청
            endpoint = "/oauth2/tokenP"
            request_body = {
                "grant_type": "client_credentials",
                "appkey": self.app_key,
                "appsecret": self.app_secret
            }
            
            try:
                response = await self._client.post(
                    endpoint,
                    json=request_body
                )
                response.raise_for_status()
                
                data = response.json()
                
                # 응답 검증
                if "access_token" not in data:
                    raise ValueError(f"Invalid token response: {data}")
                
                # AccessToken 객체 생성
                expires_in = data.get("expires_in", 86400)  # 기본 24시간
                expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
                
                token = AccessToken(
                    access_token=data["access_token"],
                    token_type=data.get("token_type", "Bearer"),
                    expires_in=expires_in,
                    expires_at=expires_at
                )
                
                # 캐시 업데이트
                self._current_token = token
                
                logger.info("Access token obtained successfully", extra=log_context(
                    expires_in=expires_in,
                    expires_at=expires_at.isoformat()
                ))
                
                return token
                
            except httpx.HTTPStatusError as e:
                logger.error(f"Token request failed: {e.response.status_code}", extra=log_context(
                    status_code=e.response.status_code,
                    response_body=e.response.text
                ))
                raise
            except Exception as e:
                logger.error(f"Unexpected error during token request: {e}")
                raise
    
    async def ensure_token(self) -> AccessToken:
        """
        유효한 토큰 보장
        만료 임박 시 자동으로 재발급합니다.
        
        Returns:
            유효한 AccessToken 객체
        """
        return await self.get_access_token(force_refresh=False)
    
    async def revoke_token(self, token: Optional[str] = None) -> bool:
        """
        토큰 폐기
        
        Args:
            token: 폐기할 토큰 (None이면 현재 토큰)
        
        Returns:
            성공 여부
        """
        if token is None and self._current_token:
            token = self._current_token.access_token
        
        if not token:
            logger.warning("No token to revoke")
            return False
        
        endpoint = "/oauth2/revokeP"
        request_body = {
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "token": token
        }
        
        try:
            response = await self._client.post(endpoint, json=request_body)
            response.raise_for_status()
            
            # 캐시 초기화
            self._current_token = None
            
            logger.info("Token revoked successfully")
            return True
            
        except Exception as e:
            logger.error(f"Token revocation failed: {e}")
            return False
    
    def get_headers(self, token: AccessToken) -> dict:
        """
        API 요청용 헤더 생성
        
        Args:
            token: Access Token 객체
        
        Returns:
            HTTP 헤더 딕셔너리
        """
        return {
            "authorization": token.authorization_header,
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "content-type": "application/json; charset=utf-8"
        }


# 전역 인증 서비스 인스턴스 (선택적 사용)
_auth_service: Optional[KISAuthService] = None


async def get_auth_service() -> KISAuthService:
    """
    전역 인증 서비스 인스턴스 반환
    
    Returns:
        KISAuthService 인스턴스
    """
    global _auth_service
    if _auth_service is None:
        _auth_service = KISAuthService()
    return _auth_service
