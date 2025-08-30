"""
데이터베이스 연결 및 세션 관리
Supabase PostgreSQL 데이터베이스와 SQLAlchemy ORM을 사용합니다.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.backend.core.config import settings
from app.backend.core.logging import get_logger

logger = get_logger(__name__)


# SQLAlchemy Base 클래스
class Base(DeclarativeBase):
    """모든 ORM 모델의 기본 클래스"""
    pass


# 비동기 엔진 생성 (환경 변수가 있을 때만)
async_engine = None
sync_engine = None

try:
    if settings.supabase_db_url and "postgresql" in settings.supabase_db_url:
        async_engine = create_async_engine(
            settings.supabase_db_url.replace("postgresql", "postgresql+asyncpg"),
            echo=settings.debug,
            pool_size=20,
            max_overflow=10,
            pool_pre_ping=True,  # 연결 상태 확인
            pool_recycle=3600,  # 1시간마다 연결 재생성
        )

        # 동기 엔진 생성 (마이그레이션용)
        sync_engine = create_engine(
            settings.supabase_db_url,
            echo=settings.debug,
            pool_size=10,
            max_overflow=5,
            pool_pre_ping=True,
            pool_recycle=3600,
        )
except Exception as e:
    logger.warning(f"Database engine creation failed: {e}. Running without database.")

# 비동기 세션 팩토리
AsyncSessionLocal = None
SyncSessionLocal = None

if async_engine:
    AsyncSessionLocal = async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

if sync_engine:
    # 동기 세션 팩토리 (Celery 워커용)
    SyncSessionLocal = sessionmaker(
        bind=sync_engine,
        class_=Session,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI 의존성 주입용 비동기 데이터베이스 세션
    
    Yields:
        AsyncSession: 비동기 데이터베이스 세션
    """
    if not AsyncSessionLocal:
        raise RuntimeError("Database not initialized")
        
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()


def get_sync_db() -> Session:
    """
    Celery 워커용 동기 데이터베이스 세션
    
    Returns:
        Session: 동기 데이터베이스 세션
    """
    if not SyncSessionLocal:
        raise RuntimeError("Database not initialized")
        
    session = SyncSessionLocal()
    try:
        return session
    except Exception as e:
        session.rollback()
        session.close()
        logger.error(f"Database session error: {e}")
        raise


@asynccontextmanager
async def async_db_context() -> AsyncGenerator[AsyncSession, None]:
    """
    비동기 컨텍스트 매니저로 데이터베이스 세션 관리
    
    Example:
        async with async_db_context() as db:
            result = await db.execute(query)
    """
    if not AsyncSessionLocal:
        raise RuntimeError("Database not initialized")
        
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database transaction error: {e}")
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    데이터베이스 초기화
    테이블 생성 및 초기 데이터 설정
    """
    if not async_engine:
        logger.warning("Database engine not available, skipping initialization")
        return
        
    try:
        async with async_engine.begin() as conn:
            # 테이블 생성 (개발 환경에서만)
            if settings.environment == "development":
                await conn.run_sync(Base.metadata.create_all)
                logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise


async def close_db() -> None:
    """데이터베이스 연결 종료"""
    if async_engine:
        await async_engine.dispose()
        logger.info("Database connections closed")
    else:
        logger.info("No database connections to close")
