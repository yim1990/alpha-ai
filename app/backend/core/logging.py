"""
구조화된 로깅 설정
개발 환경에서는 사용자 친화적 포맷, 프로덕션에서는 JSON 형식의 로그를 생성합니다.
"""

import logging
import sys
from typing import Any, Dict

import orjson
from pythonjsonlogger import jsonlogger

from app.backend.core.config import settings


class ColoredFormatter(logging.Formatter):
    """컬러 포맷터 - 개발 환경용 사용자 친화적 로그"""
    
    # ANSI 컬러 코드
    COLORS = {
        'DEBUG': '\033[36m',     # 시안
        'INFO': '\033[32m',      # 녹색  
        'WARNING': '\033[33m',   # 노란색
        'ERROR': '\033[31m',     # 빨간색
        'CRITICAL': '\033[35m',  # 자주색
        'RESET': '\033[0m'       # 리셋
    }
    
    def format(self, record):
        # 로그 레벨에 따른 색상 적용
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']
        
        # 타임스탬프 (간소화)
        timestamp = self.formatTime(record, '%H:%M:%S')
        
        # 모듈명 간소화
        module = record.module
        if len(module) > 12:
            module = module[:12] + '...'
            
        # 이모지 추가
        emoji_map = {
            'DEBUG': '🔍',
            'INFO': '✅' if '✅' in record.getMessage() else ('❌' if '❌' in record.getMessage() else '📋' if '📋' in record.getMessage() else 'ℹ️'),
            'WARNING': '⚠️',
            'ERROR': '❌',
            'CRITICAL': '🚨'
        }
        emoji = emoji_map.get(record.levelname, '')
        
        # 포맷된 로그 메시지
        formatted = f"{color}[{timestamp}] {emoji} {record.levelname:<8}{reset} {module:<15} {record.getMessage()}"
        
        return formatted


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """커스텀 JSON 로그 포매터"""
    
    def add_fields(
        self,
        log_record: Dict[str, Any],
        record: logging.LogRecord,
        message_dict: Dict[str, Any]
    ) -> None:
        """로그 레코드에 추가 필드 삽입"""
        super().add_fields(log_record, record, message_dict)
        
        # 타임스탬프 추가
        log_record["timestamp"] = self.formatTime(record, self.datefmt)
        
        # 로그 레벨 이름 추가
        log_record["level"] = record.levelname
        
        # 모듈 및 함수 정보 추가
        log_record["module"] = record.module
        log_record["function"] = record.funcName
        
        # 환경 정보 추가
        log_record["environment"] = settings.environment
        
        # 예외 정보가 있으면 추가
        if record.exc_info:
            log_record["exc_info"] = self.formatException(record.exc_info)


def setup_logging(
    log_level: str = None,
    log_format: str = None
) -> None:
    """
    애플리케이션 로깅 설정
    
    Args:
        log_level: 로그 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: 로그 형식 ("json" or "text")
    """
    log_level = log_level or settings.log_level
    log_format = log_format or settings.log_format
    
    # 루트 로거 가져오기
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level))
    
    # 기존 핸들러 제거
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 콘솔 핸들러 생성
    console_handler = logging.StreamHandler(sys.stdout)
    
    if log_format == "json":
        # JSON 포매터 설정 (프로덕션)
        formatter = CustomJsonFormatter(
            "%(timestamp)s %(level)s %(name)s %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    elif settings.environment == "development":
        # 개발 환경: 컬러 포매터 설정
        formatter = ColoredFormatter()
    else:
        # 기본 텍스트 포매터 설정
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # 외부 라이브러리 로그 레벨 조정
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    
    # Celery 로거 설정
    logging.getLogger("celery").setLevel(logging.INFO)
    logging.getLogger("celery.task").setLevel(logging.INFO)
    logging.getLogger("celery.beat").setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
    """
    모듈별 로거 인스턴스 생성
    
    Args:
        name: 로거 이름 (보통 __name__ 사용)
    
    Returns:
        Logger 인스턴스
    """
    return logging.getLogger(name)


# 구조화된 로그 데이터 생성 헬퍼
def log_context(**kwargs) -> Dict[str, Any]:
    """
    구조화된 로그 컨텍스트 생성
    
    Example:
        logger.info("Order placed", extra=log_context(
            order_id="123",
            symbol="AAPL",
            quantity=10
        ))
    """
    return {"extra": kwargs}


# 초기 로깅 설정
setup_logging()
