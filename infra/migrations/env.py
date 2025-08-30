"""
Alembic 환경 설정
데이터베이스 마이그레이션을 위한 설정을 포함합니다.
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlalchemy.ext.asyncio import AsyncEngine

# 프로젝트 모델 임포트
from app.backend.core.config import settings
from app.backend.core.database import Base
from app.backend.models import *  # 모든 모델을 임포트하여 Base.metadata에 등록

# Alembic Config 객체
config = context.config

# 로깅 설정
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 메타데이터 설정
target_metadata = Base.metadata

# 데이터베이스 URL 설정
config.set_main_option("sqlalchemy.url", settings.supabase_db_url)


def run_migrations_offline() -> None:
    """
    오프라인 모드에서 마이그레이션 실행
    데이터베이스 연결 없이 SQL 스크립트만 생성합니다.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    """마이그레이션 실행"""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """
    온라인 모드에서 마이그레이션 실행
    실제 데이터베이스에 연결하여 마이그레이션을 적용합니다.
    """
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = settings.supabase_db_url.replace(
        "postgresql+psycopg", "postgresql+asyncpg"
    )
    
    connectable = AsyncEngine(
        engine_from_config(
            configuration,
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
            future=True,
        )
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
