"""
애플리케이션 설정 관리
환경 변수를 통해 설정을 로드하고 검증합니다.
"""

from functools import lru_cache
from typing import Optional

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """애플리케이션 전역 설정"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore",
    )
    
    # 애플리케이션 설정
    app_name: str = "Alpha AI Trading System"
    app_version: str = "0.1.0"
    environment: str = Field(default="development", pattern="^(development|staging|production)$")
    debug: bool = True
    
    # API 서버 설정
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    backend_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:3000"
    
    # CORS 설정
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:3001"]
    
    # Supabase 데이터베이스
    supabase_db_url: str = Field(..., description="PostgreSQL 연결 URL")
    supabase_project_url: Optional[str] = None
    supabase_anon_key: Optional[SecretStr] = None
    supabase_service_role_key: Optional[SecretStr] = None
    
    # Redis 설정
    redis_url: str = "redis://localhost:6379/0"
    
    # KIS API 설정
    kis_app_key: SecretStr = Field(..., description="KIS API App Key")
    kis_app_secret: SecretStr = Field(..., description="KIS API App Secret")
    kis_account_no: str = Field(..., description="KIS 계좌번호 (끝 2자리 상품코드 포함)")
    kis_use_sandbox: bool = True
    
    # KIS API 엔드포인트
    @property
    def kis_base_url(self) -> str:
        """KIS API 기본 URL"""
        if self.kis_use_sandbox:
            return "https://openapivts.koreainvestment.com:29443"  # 모의투자
        return "https://openapi.koreainvestment.com:9443"  # 실거래
    
    @property
    def kis_ws_url(self) -> str:
        """KIS WebSocket URL"""
        if self.kis_use_sandbox:
            return "ws://ops.koreainvestment.com:31000"  # 모의투자
        return "ws://ops.koreainvestment.com:21000"  # 실거래
    
    # 보안 설정
    encryption_key: SecretStr = Field(
        default=SecretStr("change_this_32_byte_key_in_prod!"),
        description="AES-256 암호화 키 (32 bytes)"
    )
    jwt_secret_key: SecretStr = Field(
        default=SecretStr("change_this_secret_key_in_production"),
        description="JWT 토큰 서명 키"
    )
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 60 * 24 * 7  # 7일
    
    # Celery 설정
    celery_broker_url: str = Field(default="redis://localhost:6379/0")
    celery_result_backend: str = Field(default="redis://localhost:6379/0")
    celery_task_always_eager: bool = False  # 테스트용 (True면 동기 실행)
    
    # 로깅 설정
    log_level: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    log_format: str = "json"  # "json" or "text"
    
    # 트레이딩 설정
    max_daily_trades: int = 100  # 일일 최대 거래 횟수
    max_position_per_symbol: float = 10000  # 종목당 최대 포지션 금액 (USD)
    default_cooldown_seconds: int = 60  # 거래 실패 후 기본 쿨다운
    order_retry_max_attempts: int = 3  # 주문 재시도 최대 횟수
    
    # 미국 시장 거래 시간 (KST 기준)
    us_market_open_kst: str = "23:30"  # 전일 23:30 (서머타임 22:30)
    us_market_close_kst: str = "06:00"  # 익일 06:00 (서머타임 05:00)
    
    @field_validator("encryption_key")
    @classmethod
    def validate_encryption_key(cls, v: SecretStr) -> SecretStr:
        """암호화 키 길이 검증 (32 bytes for AES-256)"""
        if len(v.get_secret_value()) != 32:
            raise ValueError("encryption_key must be exactly 32 bytes for AES-256")
        return v
    
    @field_validator("kis_account_no")
    @classmethod
    def validate_account_no(cls, v: str) -> str:
        """계좌번호 형식 검증"""
        if not v or len(v) < 10:
            raise ValueError("Invalid KIS account number format")
        return v


@lru_cache
def get_settings() -> Settings:
    """
    설정 싱글톤 인스턴스 반환
    @lru_cache를 사용하여 한 번만 로드
    """
    return Settings()


# 전역 설정 인스턴스
settings = get_settings()
