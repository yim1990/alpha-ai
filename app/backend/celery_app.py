"""
Celery 애플리케이션 설정
백그라운드 작업 및 스케줄링을 담당합니다.
"""

from celery import Celery
from celery.schedules import crontab

from app.backend.core.config import settings
from app.backend.core.logging import get_logger, setup_logging

# 로깅 설정
setup_logging()
logger = get_logger(__name__)

# Celery 앱 생성
celery_app = Celery(
    "alpha_ai",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.backend.workers.bot",
        "app.backend.workers.scheduler",
        "app.backend.workers.market_data",
    ]
)

# Celery 설정
celery_app.conf.update(
    # 작업 설정
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Seoul",
    enable_utc=True,
    
    # 작업 라우팅
    task_routes={
        "app.backend.workers.bot.*": {"queue": "bot"},
        "app.backend.workers.scheduler.*": {"queue": "scheduler"},
        "app.backend.workers.market_data.*": {"queue": "market_data"},
    },
    
    # 작업 실행 설정
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_track_started=True,
    task_time_limit=300,  # 5분
    task_soft_time_limit=240,  # 4분
    
    # 워커 설정
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,
    worker_disable_rate_limits=False,
    
    # 결과 백엔드 설정
    result_expires=3600,  # 1시간
    
    # 동기 실행 (테스트용)
    task_always_eager=settings.celery_task_always_eager,
    task_eager_propagates=settings.celery_task_always_eager,
)

# Celery Beat 스케줄 설정
celery_app.conf.beat_schedule = {
    # 미국 장 시작 전 준비 (KST 22:00, 서머타임 21:00)
    "prepare_us_market_open": {
        "task": "app.backend.workers.scheduler.prepare_market_open",
        "schedule": crontab(hour=22, minute=0),
        "args": ("US",),
    },
    
    # 미국 장 종료 후 정리 (KST 06:30, 서머타임 05:30)
    "cleanup_us_market_close": {
        "task": "app.backend.workers.scheduler.cleanup_market_close",
        "schedule": crontab(hour=6, minute=30),
        "args": ("US",),
    },
    
    # 계좌 헬스체크 (5분마다)
    "account_health_check": {
        "task": "app.backend.workers.scheduler.check_account_health",
        "schedule": crontab(minute="*/5"),
    },
    
    # 토큰 갱신 체크 (30분마다)
    "token_refresh_check": {
        "task": "app.backend.workers.scheduler.refresh_tokens",
        "schedule": crontab(minute="*/30"),
    },
    
    # 미체결 주문 정리 (1시간마다)
    "cleanup_pending_orders": {
        "task": "app.backend.workers.scheduler.cleanup_pending_orders",
        "schedule": crontab(minute=0),
    },
    
    # 일일 리포트 생성 (매일 오전 9시)
    "daily_report": {
        "task": "app.backend.workers.scheduler.generate_daily_report",
        "schedule": crontab(hour=9, minute=0),
    },
}


@celery_app.task(bind=True)
def debug_task(self):
    """디버그 태스크"""
    logger.info(f"Request: {self.request!r}")
    return "pong"


# Celery 시그널 핸들러
@celery_app.signals.task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, **kwargs):
    """작업 실패 핸들러"""
    logger.error(f"Task {sender.name} ({task_id}) failed: {exception}")


@celery_app.signals.task_retry.connect
def task_retry_handler(sender=None, task_id=None, reason=None, **kwargs):
    """작업 재시도 핸들러"""
    logger.warning(f"Task {sender.name} ({task_id}) retrying: {reason}")


@celery_app.signals.worker_ready.connect
def worker_ready_handler(sender=None, **kwargs):
    """워커 준비 완료 핸들러"""
    logger.info(f"Worker {sender.hostname} is ready")


@celery_app.signals.worker_shutdown.connect
def worker_shutdown_handler(sender=None, **kwargs):
    """워커 종료 핸들러"""
    logger.info(f"Worker {sender.hostname} is shutting down")
