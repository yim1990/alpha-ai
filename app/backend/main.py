"""
FastAPI 메인 애플리케이션
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# .env 파일을 명시적으로 로드
env_file = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_file)
print(f"🔧 .env 파일 로드: {env_file} (존재: {env_file.exists()})")

from app.backend.core.config import settings
from app.backend.core.database import close_db, check_db_connection

# KIS API 관련 import
import os
from typing import Optional
import httpx
from app.backend.kis.auth import KISAuthService

# 전역 KIS 인증 서비스
kis_auth: Optional[KISAuthService] = None
kis_token_cache = {}


async def initialize_kis():
    """KIS API 초기화"""
    global kis_auth
    
    try:
        app_key = os.getenv("KIS_APP_KEY")
        app_secret = os.getenv("KIS_APP_SECRET") 
        use_sandbox = os.getenv("KIS_USE_SANDBOX", "true").lower() == "true"
        
        if not app_key or not app_secret:
            print("⚠️  KIS API credentials not found. Running in mock mode.")
            return False
        
        if app_key.startswith("your_") or app_secret.startswith("your_"):
            print("⚠️  KIS API credentials are placeholder values. Running in mock mode.")
            return False
        
        kis_auth = KISAuthService(
            app_key=app_key,
            app_secret=app_secret,
            use_sandbox=use_sandbox
        )
        
        # 토큰 발급 테스트
        token = await kis_auth.get_access_token()
        kis_token_cache["token"] = token
        kis_token_cache["timestamp"] = datetime.now(timezone.utc)
        
        print("✅ KIS API initialized successfully")
        return True
        
    except ValueError as e:
        if "rate limit" in str(e).lower():
            print(f"⚠️  KIS API rate limit exceeded: {e}")
            print("⏰ Please wait at least 1 minute before restarting the server")
            return False
        else:
            print(f"❌ KIS API initialization failed: {e}")
            return False
    except Exception as e:
        print(f"❌ KIS API initialization failed: {e}")
        return False


async def get_market_data_from_kis(symbol: str) -> Optional[dict]:
    """KIS API에서 실시간 시세 조회"""
    global kis_auth, kis_token_cache
    
    if not kis_auth:
        return None
    
    try:
        # 캐시된 토큰 사용
        token = kis_token_cache.get("token")
        if not token or token.is_expired:
            print(f"⚠️  Token expired for {symbol}, using cached token anyway")
        
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
                    # 회사명 매핑
                    company_names = {
                        "AAPL": "Apple Inc.",
                        "TSLA": "Tesla Inc.",
                        "NVDA": "NVIDIA Corporation",
                        "MSFT": "Microsoft Corporation",
                        "GOOGL": "Alphabet Inc."
                    }
                    
                    price = float(output.get("last", 0)) if output.get("last") else 0
                    prev_close = float(output.get("base", 0)) if output.get("base") else 0
                    change = price - prev_close if price and prev_close else 0
                    change_percent = (change / prev_close * 100) if prev_close else 0
                    
                    # 시가총액 계산 (간단한 추정)
                    market_caps = {
                        "AAPL": "2.7T",
                        "TSLA": "792B", 
                        "NVDA": "2.2T",
                        "MSFT": "2.8T",
                        "GOOGL": "1.7T"
                    }
                    
                    return {
                        "symbol": symbol,
                        "name": company_names.get(symbol, symbol),
                        "price": price,
                        "change": change,
                        "change_percent": change_percent,
                        "volume": int(output.get("tvol", 0)) if output.get("tvol") else 0,
                        "market_cap": market_caps.get(symbol, "N/A"),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "source": "KIS_API"
                    }
        
        return None
        
    except Exception as e:
        print(f"❌ Failed to get market data for {symbol}: {e}")
        return None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    애플리케이션 생명주기 관리
    시작 시 DB 및 KIS API 초기화, 종료 시 정리 작업을 수행합니다.
    """
    # 시작 시
    print("🚀 Starting Alpha AI Trading System...")
    
    # 데이터베이스 연결 확인
    db_connected = await check_db_connection()
    
    if not db_connected:
        print("❌ 데이터베이스 연결 실패 - 서버를 종료합니다")
        print("💡 .env 파일의 데이터베이스 설정을 확인해주세요")
        raise RuntimeError("Database connection failed. Cannot start server without database.")
    
    print("✅ Database connection successful")
    
    # KIS API 초기화
    print("🔗 KIS API 연결 시도...")
    kis_success = await initialize_kis()
    
    if kis_success:
        print("✅ KIS API 연결 성공!")
        print("📊 실시간 데이터 사용 가능")
        print("💾 토큰 캐싱 활성화 - 서버 재시작 후에도 토큰 재사용")
    else:
        print("⚠️  KIS API 연결 실패")
        print("🔄 모의 데이터 모드로 실행")
    
    print("✅ Server ready to start")
    
    yield
    
    # 종료 시
    print("🔄 Shutting down Alpha AI Trading System...")
    
    global kis_auth
    if kis_auth:
        await kis_auth.close()
        print("✅ KIS API connection closed")
    
    await close_db()
    print("✅ Application shutdown complete")


# FastAPI 앱 생성
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    docs_url="/api/docs" if settings.debug else None,
    redoc_url="/api/redoc" if settings.debug else None,
    lifespan=lifespan
)

# CORS 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 헬스체크 엔드포인트
@app.get("/health")
async def health_check():
    """
    시스템 헬스체크
    """
    from app.backend.core.database import check_db_connection
    
    db_connected = await check_db_connection()
    
    return {
        "status": "healthy" if db_connected else "degraded",
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "database_connected": db_connected,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# KIS API 통합 엔드포인트들
@app.get("/api/kis/status")
async def get_kis_status():
    """KIS API 상태 조회"""
    global kis_auth, kis_token_cache
    
    token = kis_token_cache.get("token")
    is_connected = bool(kis_auth and token)
    
    return {
        "connected": is_connected,
        "sandbox_mode": os.getenv("KIS_USE_SANDBOX", "true").lower() == "true",
        "token_valid": bool(token and not token.is_expired) if token else False,
        "last_check": datetime.now(timezone.utc).isoformat(),
        "rate_limit": {
            "remaining": 95,  # TODO: 실제 API 호출 수 추적
            "total": 100,
            "reset_at": datetime.now(timezone.utc).isoformat()
        }
    }

@app.get("/api/market/{symbol}")
async def get_market_data(symbol: str):
    """실시간 주식 데이터 조회 (KIS API 우선, 실패 시 목업)"""
    # KIS API에서 실제 데이터 조회 시도
    market_data = await get_market_data_from_kis(symbol.upper())
    
    if market_data:
        return market_data
    
    # KIS API 실패 시 목업 데이터 반환
    print(f"⚠️  KIS API failed for {symbol}, using mock data")
    
    mock_data = {
        "AAPL": {
            "symbol": "AAPL",
            "name": "Apple Inc.",
            "price": 174.50,
            "change": 2.30,
            "change_percent": 1.33,
            "volume": 52040000,
            "market_cap": "2.7T"
        },
        "TSLA": {
            "symbol": "TSLA", 
            "name": "Tesla Inc.",
            "price": 248.87,
            "change": -5.23,
            "change_percent": -2.06,
            "volume": 89420000,
            "market_cap": "792B"
        },
        "NVDA": {
            "symbol": "NVDA",
            "name": "NVIDIA Corporation", 
            "price": 875.30,
            "change": 15.67,
            "change_percent": 1.82,
            "volume": 42100000,
            "market_cap": "2.2T"
        }
    }
    
    if symbol.upper() in mock_data:
        data = mock_data[symbol.upper()]
        data["timestamp"] = datetime.now(timezone.utc).isoformat()
        data["source"] = "mock_data"
        return data
    else:
        return JSONResponse(
            status_code=404,
            content={"error": f"Symbol {symbol} not found"}
        )

@app.get("/api/dashboard/stats")
async def get_dashboard_stats():
    """대시보드 통계 데이터 (실시간 데이터 포함)"""
    global kis_auth, kis_token_cache
    
    kis_connected = bool(kis_auth and kis_token_cache.get("token"))
    
    # 주요 종목들의 실시간 가격 조회
    symbols = ["AAPL", "TSLA", "NVDA"]
    total_value = 0
    
    for symbol in symbols:
        market_data = await get_market_data_from_kis(symbol)
        if market_data and market_data.get("price"):
            # 가상의 보유 수량
            holdings = {"AAPL": 50, "TSLA": 20, "NVDA": 15}
            total_value += market_data["price"] * holdings.get(symbol, 0)
    
    # 모의 데이터로 보완
    if total_value == 0:
        total_value = 45750.30
    
    return {
        "total_accounts": 3,
        "active_accounts": 2 if kis_connected else 0,
        "total_rules": 8,
        "active_rules": 5 if kis_connected else 0,
        "total_positions": 12,
        "total_value_usd": total_value,
        "daily_pnl": 1250.75,
        "daily_pnl_percent": 2.81,
        "last_updated": datetime.now(timezone.utc).isoformat()
    }

@app.get("/api/system/status")
async def get_system_status():
    """시스템 상태 조회"""
    global kis_auth, kis_token_cache
    
    kis_connected = bool(kis_auth and kis_token_cache.get("token"))
    db_connected = await check_db_connection()
    
    return {
        "api_server": "connected",
        "kis_api": "connected" if kis_connected else "disconnected", 
        "database": "connected" if db_connected else "disconnected",
        "websocket": "ready",
        "trading_bot": "ready" if kis_connected else "standby",
        "data_sync": "synced" if kis_connected else "mock_mode",
        "last_update": datetime.now(timezone.utc).isoformat()
    }

# API 라우터 등록
from app.backend.routes.auth import router as auth_router

app.include_router(auth_router, prefix="/api")

# 추후 구현될 라우터들
# from app.backend.routes import accounts, rules, orders, positions, logs
# app.include_router(accounts.router, prefix="/api/accounts", tags=["accounts"])
# app.include_router(rules.router, prefix="/api/rules", tags=["rules"])
# app.include_router(orders.router, prefix="/api/orders", tags=["orders"])
# app.include_router(positions.router, prefix="/api/positions", tags=["positions"])
# app.include_router(logs.router, prefix="/api/logs", tags=["logs"])


# 전역 예외 핸들러
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    전역 예외 처리
    """
    print(f"❌ Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc) if settings.debug else "An error occurred"
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.backend.main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
