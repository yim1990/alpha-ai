"""
KIS API HashKey 서비스
주문 요청에 필요한 HashKey(서명) 생성을 담당합니다.
"""

import hashlib
import hmac
import json
from typing import Any, Dict, Optional

from app.backend.core.config import settings
from app.backend.core.logging import get_logger

logger = get_logger(__name__)


class HashKeyService:
    """
    KIS API HashKey 생성 서비스
    주문/정정/취소 등 중요 요청에 필요한 서명을 생성합니다.
    """
    
    def __init__(
        self,
        app_key: Optional[str] = None,
        app_secret: Optional[str] = None
    ):
        """
        Args:
            app_key: KIS API App Key
            app_secret: KIS API App Secret
        """
        self.app_key = app_key or settings.kis_app_key.get_secret_value()
        self.app_secret = app_secret or settings.kis_app_secret.get_secret_value()
    
    def generate_hashkey(self, data: Dict[str, Any]) -> str:
        """
        HashKey 생성
        
        KIS API 명세에 따라 요청 바디를 HMAC-SHA256으로 서명합니다.
        
        Args:
            data: 요청 바디 데이터 (딕셔너리)
        
        Returns:
            Base64 인코딩된 HashKey 문자열
        """
        try:
            # JSON 문자열로 변환 (공백 없이, 키 정렬)
            json_data = json.dumps(data, separators=(',', ':'), ensure_ascii=False)
            
            # HMAC-SHA256 서명 생성
            signature = hmac.new(
                self.app_secret.encode('utf-8'),
                json_data.encode('utf-8'),
                hashlib.sha256
            ).digest()
            
            # Base64 인코딩
            import base64
            hashkey = base64.b64encode(signature).decode('utf-8')
            
            logger.debug(f"HashKey generated for data: {len(json_data)} bytes")
            
            return hashkey
            
        except Exception as e:
            logger.error(f"HashKey generation failed: {e}")
            raise
    
    def sign_order(self, order_data: Dict[str, Any]) -> str:
        """
        주문 데이터 서명
        
        Args:
            order_data: 주문 요청 데이터
        
        Returns:
            HashKey 문자열
        """
        # 주문 데이터 검증
        required_fields = ["CANO", "ACNT_PRDT_CD", "PDNO"]
        for field in required_fields:
            if field not in order_data:
                raise ValueError(f"Missing required field for order: {field}")
        
        # HashKey 생성
        hashkey = self.generate_hashkey(order_data)
        
        logger.info(f"Order signed - Symbol: {order_data.get('PDNO')}")
        
        return hashkey
    
    def sign_cancel(self, cancel_data: Dict[str, Any]) -> str:
        """
        주문 취소 데이터 서명
        
        Args:
            cancel_data: 취소 요청 데이터
        
        Returns:
            HashKey 문자열
        """
        # 취소 데이터 검증
        required_fields = ["CANO", "ACNT_PRDT_CD", "ORGN_ODNO"]
        for field in required_fields:
            if field not in cancel_data:
                raise ValueError(f"Missing required field for cancel: {field}")
        
        # HashKey 생성
        hashkey = self.generate_hashkey(cancel_data)
        
        logger.info(f"Cancel order signed - Order ID: {cancel_data.get('ORGN_ODNO')}")
        
        return hashkey
    
    def sign_modify(self, modify_data: Dict[str, Any]) -> str:
        """
        주문 정정 데이터 서명
        
        Args:
            modify_data: 정정 요청 데이터
        
        Returns:
            HashKey 문자열
        """
        # 정정 데이터 검증
        required_fields = ["CANO", "ACNT_PRDT_CD", "ORGN_ODNO"]
        for field in required_fields:
            if field not in modify_data:
                raise ValueError(f"Missing required field for modify: {field}")
        
        # HashKey 생성
        hashkey = self.generate_hashkey(modify_data)
        
        logger.info(f"Modify order signed - Order ID: {modify_data.get('ORGN_ODNO')}")
        
        return hashkey


# 전역 HashKey 서비스 인스턴스
_hashkey_service: Optional[HashKeyService] = None


def get_hashkey_service() -> HashKeyService:
    """
    전역 HashKey 서비스 인스턴스 반환
    
    Returns:
        HashKeyService 인스턴스
    """
    global _hashkey_service
    if _hashkey_service is None:
        _hashkey_service = HashKeyService()
    return _hashkey_service
