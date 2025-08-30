"""
FastAPI 메인 애플리케이션
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.backend.core.config import settings
from app.backend.core.database import init_db, close_db
from app.backend.core.logging import get_logger, setup_logging

# 로깅 설정
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    애플리케이션 생명주기 관리
    시작 시 DB 초기화, 종료 시 정리 작업을 수행합니다.
    """
    # 시작 시
    logger.info("Starting Alpha AI Trading System...")
    await init_db()
    logger.info("Database initialized")
    
    yield
    
    # 종료 시
    logger.info("Shutting down Alpha AI Trading System...")
    await close_db()
    logger.info("Database connections closed")


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
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment
    }


# API 라우터 등록 (추후 구현)
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
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
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
