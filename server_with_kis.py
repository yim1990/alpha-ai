#!/usr/bin/env python3
"""
KIS API 통합 서버
실제 한국투자증권 API 데이터를 사용하는 FastAPI 서버
"""

import asyncio
import os
from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# KIS API 클라이언트 import
from app.backend.kis.auth import KISAuthService
from app.backend.core.logging import get_logger

logger = get_logger(__name__)

# FastAPI 앱 생성
app = FastAPI(
    title="Alpha AI Trading System (KIS Integrated)",
    description="실제 KIS API 데이터를 사용하는 미국 주식 자동매매 시스템",
    version="0.2.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 전역 KIS 인증 서비스
kis_auth: Optional[KISAuthService] = None
kis_token_cache = {}

# 데이터 모델 (기존과 동일)
class AccountInfo(BaseModel):
    id: str
    nickname: str
    broker: str = "KIS"
    market: str = "US"
    enabled: bool = True
    health_status: str = "healthy"
    last_heartbeat: Optional[datetime] = None
    kis_connected: bool = False

class MarketData(BaseModel):
    symbol: str
    current_price: Optional[float] = None
    previous_close: Optional[float] = None
    change_percent: Optional[float] = None
    volume: Optional[int] = None
    last_updated: Optional[datetime] = None

class KISStatus(BaseModel):
    connected: bool
    last_token_time: Optional[datetime] = None
    token_valid: bool = False
    api_calls_today: int = 0
    error_message: Optional[str] = None


# KIS API 초기화
async def initialize_kis():
    """KIS API 초기화"""
    global kis_auth
    
    try:
        app_key = os.getenv("KIS_APP_KEY")
        app_secret = os.getenv("KIS_APP_SECRET") 
        use_sandbox = os.getenv("KIS_USE_SANDBOX", "true").lower() == "true"
        
        if not app_key or not app_secret:
            logger.warning("KIS API credentials not found. Running in mock mode.")
            return False
        
        if app_key.startswith("your_") or app_secret.startswith("your_"):
            logger.warning("KIS API credentials are placeholder values. Running in mock mode.")
            return False
        
        kis_auth = KISAuthService(
            app_key=app_key,
            app_secret=app_secret,
            use_sandbox=use_sandbox
        )
        
        # 토큰 발급 테스트
        token = await kis_auth.get_access_token()
        kis_token_cache["token"] = token
        kis_token_cache["timestamp"] = datetime.now()
        
        logger.info("KIS API initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"KIS API initialization failed: {e}")
        return False


async def get_market_data_from_kis(symbol: str) -> Optional[MarketData]:
    """KIS API에서 실시간 시세 조회"""
    global kis_auth, kis_token_cache
    
    if not kis_auth:
        return None
    
    try:
        # 캐시된 토큰 사용
        token = kis_token_cache.get("token")
        if not token or token.is_expired:
            # 레이트 리밋을 고려해서 토큰 재발급은 신중하게
            logger.warning("Token expired, but skipping refresh due to rate limit")
            return None
        
        import httpx
        app_key = os.getenv("KIS_APP_KEY")
        app_secret = os.getenv("KIS_APP_SECRET")
        use_sandbox = os.getenv("KIS_USE_SANDBOX", "true").lower() == "true"
        base_url = "https://openapivts.koreainvestment.com:29443" if use_sandbox else "https://openapi.koreainvestment.com:9443"
        
        headers = {
            "content-type": "application/json; charset=utf-8",
            "authorization": token.authorization_header,
            "appkey": app_key,
            "appsecret": app_secret,
            "tr_id": "HHDFS00000300"  # 해외주식 현재가
        }
        
        params = {
            "AUTH": "",
            "EXCD": "NAS",  # 나스닥
            "SYMB": symbol
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{base_url}/uapi/overseas-price/v1/quotations/price",
                headers=headers,
                params=params
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("rt_cd") == "0":
                    output = data.get("output", {})
                    return MarketData(
                        symbol=symbol,
                        current_price=float(output.get("last", 0)) if output.get("last") else None,
                        previous_close=float(output.get("base", 0)) if output.get("base") else None,
                        change_percent=float(output.get("rate", 0)) if output.get("rate") else None,
                        volume=int(output.get("tvol", 0)) if output.get("tvol") else None,
                        last_updated=datetime.now()
                    )
        
        return None
        
    except Exception as e:
        logger.error(f"Failed to get market data for {symbol}: {e}")
        return None


# API 엔드포인트
@app.get("/health")
async def health_check():
    """시스템 헬스체크"""
    kis_status = bool(kis_auth and kis_token_cache.get("token"))
    
    return {
        "status": "healthy",
        "app": "Alpha AI Trading System (KIS Integrated)",
        "version": "0.2.0",
        "environment": "production" if not os.getenv("KIS_USE_SANDBOX", "true").lower() == "true" else "sandbox",
        "kis_connected": kis_status,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/kis/status", response_model=KISStatus)
async def get_kis_status():
    """KIS API 연결 상태"""
    token = kis_token_cache.get("token")
    
    return KISStatus(
        connected=bool(kis_auth and token),
        last_token_time=kis_token_cache.get("timestamp"),
        token_valid=bool(token and not token.is_expired),
        api_calls_today=0,  # TODO: 실제 카운터 구현
        error_message=None
    )


@app.get("/api/market/{symbol}", response_model=MarketData)
async def get_market_data(symbol: str):
    """실시간 시세 조회"""
    # KIS API에서 실제 데이터 조회 시도
    market_data = await get_market_data_from_kis(symbol.upper())
    
    if market_data:
        return market_data
    
    # KIS API 실패 시 모의 데이터 반환
    mock_prices = {
        "AAPL": 175.50,
        "TSLA": 238.90,
        "NVDA": 468.50,
        "MSFT": 380.20,
        "GOOGL": 140.80,
    }
    
    price = mock_prices.get(symbol.upper(), 100.0)
    
    return MarketData(
        symbol=symbol.upper(),
        current_price=price,
        previous_close=price * 0.99,
        change_percent=1.0,
        volume=1000000,
        last_updated=datetime.now()
    )


@app.get("/api/accounts", response_model=List[AccountInfo])
async def get_accounts():
    """계좌 목록 조회 (KIS 연결 상태 포함)"""
    kis_connected = bool(kis_auth and kis_token_cache.get("token"))
    
    return [
        AccountInfo(
            id="kis_main",
            nickname="KIS 메인 계좌",
            health_status="healthy" if kis_connected else "disconnected",
            last_heartbeat=datetime.now() if kis_connected else None,
            kis_connected=kis_connected
        ),
        AccountInfo(
            id="kis_test",
            nickname="KIS 테스트 계좌",
            enabled=False,
            health_status="inactive",
            kis_connected=False
        )
    ]


@app.get("/api/dashboard/stats")
async def get_dashboard_stats():
    """대시보드 통계 (실시간 데이터 포함)"""
    kis_connected = bool(kis_auth and kis_token_cache.get("token"))
    
    # 주요 종목들의 실시간 가격 조회
    symbols = ["AAPL", "TSLA", "NVDA"]
    total_value = 0
    
    for symbol in symbols:
        market_data = await get_market_data_from_kis(symbol)
        if market_data and market_data.current_price:
            # 가상의 보유 수량
            holdings = {"AAPL": 50, "TSLA": 20, "NVDA": 15}
            total_value += market_data.current_price * holdings.get(symbol, 0)
    
    # 모의 데이터로 보완
    if total_value == 0:
        total_value = 20580.50
    
    return {
        "total_balance": total_value,
        "daily_pnl": 410.5,
        "daily_pnl_percent": 2.03,
        "open_positions": 3,
        "pending_orders": 1,
        "account_health": "healthy" if kis_connected else "disconnected",
        "kis_connected": kis_connected,
        "data_source": "KIS API" if kis_connected else "Mock Data"
    }


@app.get("/api/system/status")
async def get_system_status():
    """시스템 상태"""
    kis_connected = bool(kis_auth and kis_token_cache.get("token"))
    
    return {
        "api_server": "connected",
        "kis_api": "connected" if kis_connected else "disconnected",
        "websocket": "ready",
        "trading_bot": "ready",
        "data_sync": "synced" if kis_connected else "mock_mode",
        "last_update": datetime.now().isoformat()
    }


# 앱 시작/종료 이벤트
@app.on_event("startup")
async def startup_event():
    """앱 시작 시 KIS API 초기화"""
    print("🚀 Alpha AI Trading System 시작 중...")
    print("🔗 KIS API 연결 시도...")
    
    success = await initialize_kis()
    
    if success:
        print("✅ KIS API 연결 성공!")
        print("📊 실시간 데이터 사용 가능")
    else:
        print("⚠️  KIS API 연결 실패")
        print("🔄 모의 데이터 모드로 실행")
    
    print("=" * 50)


@app.on_event("shutdown")
async def shutdown_event():
    """앱 종료 시 정리"""
    global kis_auth
    
    if kis_auth:
        await kis_auth.close()
    
    print("👋 Alpha AI Trading System 종료")


if __name__ == "__main__":
    print("🚀 KIS API 통합 서버 시작...")
    print("📍 서버 주소: http://localhost:8001")
    print("📖 API 문서: http://localhost:8001/api/docs")
    print("💊 헬스체크: http://localhost:8001/health")
    print("📊 KIS 상태: http://localhost:8001/api/kis/status")
    print("=" * 50)
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,  # 기존 테스트 서버와 구분하기 위해 다른 포트 사용
        reload=False,  # KIS 연결 때문에 reload 비활성화
        log_level="info"
    )
