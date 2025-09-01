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


# SQLAlchemy Base 클래스
class Base(DeclarativeBase):
    """모든 ORM 모델의 기본 클래스"""
    pass


# 비동기 엔진 생성 (환경 변수가 있을 때만)
async_engine = None
sync_engine = None

try:
    database_url = settings.database_url
    if database_url and "postgresql" in database_url:
        print(f"🔗 데이터베이스 URL 생성됨: {database_url[:50]}...")
        
        async_engine = create_async_engine(
            database_url,
            echo=settings.debug,
            pool_size=20,
            max_overflow=10,
            pool_pre_ping=True,  # 연결 상태 확인
            pool_recycle=3600,  # 1시간마다 연결 재생성
        )

        # 동기 엔진 생성 (마이그레이션용) - asyncpg를 psycopg2로 변경
        sync_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
        sync_engine = create_engine(
            sync_url,
            echo=settings.debug,
            pool_size=10,
            max_overflow=5,
            pool_pre_ping=True,
            pool_recycle=3600,
        )
except Exception as e:
    print(f"⚠️ Database engine creation failed: {e}. Running without database.")

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
            print(f"❌ Database session error: {e}")
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
        print(f"❌ Database session error: {e}")
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
            print(f"❌ Database transaction error: {e}")
            raise
        finally:
            await session.close()


async def check_db_connection() -> bool:
    """
    데이터베이스 연결 상태를 확인합니다.
    
    Returns:
        연결 성공 시 True, 실패 시 False
    """
    if not async_engine:
        print("❌ Database engine not configured")
        return False
        
    try:
        async with async_engine.begin() as conn:
            # 간단한 쿼리로 연결 테스트
            from sqlalchemy import text
            result = await conn.execute(text("SELECT 1"))
            result.scalar()
            print("✅ Database connection successful")
            return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False


async def init_db() -> None:
    """
    데이터베이스 연결 확인
    서버 시작 시 데이터베이스 연결 상태만 확인합니다.
    """
    if not async_engine:
        print("❌ Database engine not available")
        return
    
    # 데이터베이스 연결 상태 확인
    connection_ok = await check_db_connection()
    if not connection_ok:
        print("❌ Database connection verification failed")
        return
        
    print("✅ Database connection verified")


async def close_db() -> None:
    """데이터베이스 연결 종료"""
    if async_engine:
        await async_engine.dispose()
        print("✅ Database connections closed")
    else:
        print("ℹ️ No database connections to close")
