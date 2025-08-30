#!/usr/bin/env python3
"""
Alpha AI Trading System - 테스트 서버
현재 구현된 기능들을 테스트하기 위한 간단한 서버입니다.
"""

from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# FastAPI 앱 생성
app = FastAPI(
    title="Alpha AI Trading System",
    description="KIS Open API 기반 미국 주식 자동매매 시스템",
    version="0.1.0",
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

# 임시 데이터 모델
class AccountInfo(BaseModel):
    id: str
    nickname: str
    broker: str = "KIS"
    market: str = "US"
    enabled: bool = True
    health_status: str = "healthy"
    last_heartbeat: Optional[datetime] = None

class PositionInfo(BaseModel):
    symbol: str
    quantity: int
    avg_price: float
    current_price: float
    unrealized_pnl: float
    unrealized_pnl_percent: float

class OrderInfo(BaseModel):
    id: str
    symbol: str
    side: str  # BUY/SELL
    quantity: int
    price: Optional[float]
    status: str
    placed_at: Optional[datetime]

# 임시 데이터
mock_accounts = [
    AccountInfo(
        id="acc_001",
        nickname="메인 계좌",
        last_heartbeat=datetime.now()
    ),
    AccountInfo(
        id="acc_002", 
        nickname="테스트 계좌",
        enabled=False,
        health_status="inactive"
    )
]

mock_positions = [
    PositionInfo(
        symbol="AAPL",
        quantity=50,
        avg_price=170.20,
        current_price=175.50,
        unrealized_pnl=265.00,
        unrealized_pnl_percent=3.11
    ),
    PositionInfo(
        symbol="TSLA",
        quantity=20,
        avg_price=245.50,
        current_price=238.90,
        unrealized_pnl=-132.00,
        unrealized_pnl_percent=-2.69
    ),
    PositionInfo(
        symbol="NVDA",
        quantity=15,
        avg_price=450.00,
        current_price=468.50,
        unrealized_pnl=277.50,
        unrealized_pnl_percent=4.11
    )
]

mock_orders = [
    OrderInfo(
        id="ord_001",
        symbol="AAPL",
        side="BUY",
        quantity=10,
        price=175.50,
        status="filled",
        placed_at=datetime.now()
    ),
    OrderInfo(
        id="ord_002",
        symbol="MSFT",
        side="SELL",
        quantity=5,
        price=380.20,
        status="filled",
        placed_at=datetime.now()
    ),
    OrderInfo(
        id="ord_003",
        symbol="GOOGL",
        side="BUY",
        quantity=3,
        price=140.80,
        status="pending",
        placed_at=datetime.now()
    )
]

# API 엔드포인트

@app.get("/health")
async def health_check():
    """시스템 헬스체크"""
    return {
        "status": "healthy",
        "app": "Alpha AI Trading System",
        "version": "0.1.0",
        "environment": "test",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/")
async def root():
    """API 루트"""
    return {
        "message": "Alpha AI Trading System API",
        "version": "0.1.0",
        "docs_url": "/api/docs",
        "health_url": "/health"
    }

@app.get("/api/accounts", response_model=List[AccountInfo])
async def get_accounts():
    """계좌 목록 조회"""
    return mock_accounts

@app.get("/api/accounts/{account_id}", response_model=AccountInfo)
async def get_account(account_id: str):
    """특정 계좌 조회"""
    for account in mock_accounts:
        if account.id == account_id:
            return account
    raise HTTPException(status_code=404, detail="Account not found")

@app.get("/api/positions", response_model=List[PositionInfo])
async def get_positions(account_id: Optional[str] = None):
    """포지션 목록 조회"""
    # account_id는 현재 무시하고 모든 포지션 반환
    return mock_positions

@app.get("/api/orders", response_model=List[OrderInfo])
async def get_orders(account_id: Optional[str] = None):
    """주문 내역 조회"""
    # account_id는 현재 무시하고 모든 주문 반환
    return mock_orders

@app.get("/api/dashboard/stats")
async def get_dashboard_stats():
    """대시보드 통계 데이터"""
    total_balance = sum(p.quantity * p.current_price for p in mock_positions)
    total_pnl = sum(p.unrealized_pnl for p in mock_positions)
    
    return {
        "total_balance": total_balance,
        "daily_pnl": total_pnl,
        "daily_pnl_percent": (total_pnl / (total_balance - total_pnl)) * 100 if total_balance > total_pnl else 0,
        "open_positions": len(mock_positions),
        "pending_orders": len([o for o in mock_orders if o.status == "pending"]),
        "account_health": "healthy"
    }

@app.get("/api/system/status")
async def get_system_status():
    """시스템 상태 조회"""
    return {
        "api_server": "connected",
        "websocket": "connected", 
        "trading_bot": "running",
        "data_sync": "synced",
        "last_update": datetime.now().isoformat()
    }

if __name__ == "__main__":
    print("🚀 Alpha AI Trading System 테스트 서버 시작...")
    print("📍 서버 주소: http://localhost:8000")
    print("📖 API 문서: http://localhost:8000/api/docs")
    print("💊 헬스체크: http://localhost:8000/health")
    print("=" * 50)
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )