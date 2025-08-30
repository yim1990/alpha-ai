"""
KIS API 실시간 WebSocket 클라이언트
실시간 호가 및 체결 데이터를 수신합니다.
"""

import asyncio
import json
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Callable, Dict, Optional, Set

import websockets
from pydantic import BaseModel, Field

from app.backend.core.config import settings
from app.backend.core.logging import get_logger, log_context
from app.backend.kis.auth import KISAuthService, get_auth_service

logger = get_logger(__name__)


class MessageType(str, Enum):
    """WebSocket 메시지 타입"""
    PINGPONG = "PINGPONG"
    SUBSCRIBE = "SUBSCRIBE"
    UNSUBSCRIBE = "UNSUBSCRIBE"
    ERROR = "ERROR"
    REALTIME = "REALTIME"


class RealtimeData(BaseModel):
    """실시간 데이터 모델"""
    
    symbol: str = Field(..., description="종목코드")
    timestamp: datetime = Field(..., description="수신시각")
    data_type: str = Field(..., description="데이터 타입")
    
    # 호가 데이터
    bid_price: Optional[Decimal] = Field(None, description="매수호가")
    bid_size: Optional[int] = Field(None, description="매수호가수량")
    ask_price: Optional[Decimal] = Field(None, description="매도호가")
    ask_size: Optional[int] = Field(None, description="매도호가수량")
    
    # 체결 데이터
    last_price: Optional[Decimal] = Field(None, description="현재가")
    last_size: Optional[int] = Field(None, description="체결수량")
    volume: Optional[int] = Field(None, description="거래량")
    
    # 추가 정보
    change: Optional[Decimal] = Field(None, description="전일대비")
    change_rate: Optional[Decimal] = Field(None, description="등락률")


class RealtimeClient:
    """
    KIS 실시간 WebSocket 클라이언트
    호가/체결 데이터를 실시간으로 수신하고 처리합니다.
    """
    
    def __init__(
        self,
        auth_service: Optional[KISAuthService] = None,
        use_sandbox: Optional[bool] = None,
        on_data: Optional[Callable[[RealtimeData], None]] = None,
        on_error: Optional[Callable[[str], None]] = None
    ):
        """
        Args:
            auth_service: 인증 서비스
            use_sandbox: 모의투자 사용 여부
            on_data: 데이터 수신 콜백
            on_error: 에러 발생 콜백
        """
        self.auth_service = auth_service
        self.use_sandbox = use_sandbox if use_sandbox is not None else settings.kis_use_sandbox
        self.ws_url = settings.kis_ws_url
        
        # WebSocket 연결
        self._websocket: Optional[websockets.WebSocketClientProtocol] = None
        self._connection_key: Optional[str] = None
        
        # 구독 관리
        self._subscriptions: Set[str] = set()
        self._subscription_lock = asyncio.Lock()
        
        # 콜백 함수
        self.on_data = on_data
        self.on_error = on_error
        
        # 연결 상태
        self._connected = False
        self._running = False
        self._reconnect_task: Optional[asyncio.Task] = None
        
        # 핑퐁 관리
        self._last_ping_time: Optional[datetime] = None
        self._ping_task: Optional[asyncio.Task] = None
    
    async def connect(self) -> bool:
        """
        WebSocket 연결 수립
        
        Returns:
            연결 성공 여부
        """
        try:
            # 인증 서비스 초기화
            if not self.auth_service:
                self.auth_service = await get_auth_service()
            
            # 접속키 발급
            await self._get_connection_key()
            
            # WebSocket 연결
            logger.info(f"Connecting to WebSocket: {self.ws_url}")
            self._websocket = await websockets.connect(
                self.ws_url,
                ping_interval=20,
                ping_timeout=10
            )
            
            self._connected = True
            self._running = True
            
            # 수신 태스크 시작
            asyncio.create_task(self._receive_loop())
            
            # 핑퐁 태스크 시작
            self._ping_task = asyncio.create_task(self._ping_loop())
            
            logger.info("WebSocket connected successfully")
            return True
            
        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}")
            self._connected = False
            return False
    
    async def disconnect(self) -> None:
        """WebSocket 연결 종료"""
        self._running = False
        
        # 핑퐁 태스크 취소
        if self._ping_task:
            self._ping_task.cancel()
        
        # 재연결 태스크 취소
        if self._reconnect_task:
            self._reconnect_task.cancel()
        
        # WebSocket 연결 종료
        if self._websocket:
            await self._websocket.close()
            self._websocket = None
        
        self._connected = False
        self._subscriptions.clear()
        
        logger.info("WebSocket disconnected")
    
    async def subscribe(self, symbol: str, data_types: list[str] = None) -> bool:
        """
        종목 구독
        
        Args:
            symbol: 종목코드
            data_types: 구독할 데이터 타입 리스트 (기본: 호가, 체결)
        
        Returns:
            구독 성공 여부
        """
        if not self._connected:
            logger.error("WebSocket not connected")
            return False
        
        if data_types is None:
            data_types = ["H0STCNT0", "H0STCNI0"]  # 호가, 체결
        
        async with self._subscription_lock:
            for data_type in data_types:
                try:
                    # 구독 메시지 생성
                    subscribe_msg = {
                        "header": {
                            "approval_key": self._connection_key,
                            "custtype": "P",
                            "tr_type": "1",  # 1: 구독
                            "content-type": "utf-8"
                        },
                        "body": {
                            "input": {
                                "tr_id": data_type,
                                "tr_key": symbol
                            }
                        }
                    }
                    
                    # 구독 요청 전송
                    await self._websocket.send(json.dumps(subscribe_msg))
                    
                    # 구독 목록에 추가
                    subscription_key = f"{data_type}:{symbol}"
                    self._subscriptions.add(subscription_key)
                    
                    logger.info(f"Subscribed to {symbol} - {data_type}")
                    
                except Exception as e:
                    logger.error(f"Subscribe failed for {symbol}: {e}")
                    return False
        
        return True
    
    async def unsubscribe(self, symbol: str, data_types: list[str] = None) -> bool:
        """
        종목 구독 해제
        
        Args:
            symbol: 종목코드
            data_types: 구독 해제할 데이터 타입 리스트
        
        Returns:
            구독 해제 성공 여부
        """
        if not self._connected:
            return False
        
        if data_types is None:
            data_types = ["H0STCNT0", "H0STCNI0"]
        
        async with self._subscription_lock:
            for data_type in data_types:
                try:
                    # 구독 해제 메시지 생성
                    unsubscribe_msg = {
                        "header": {
                            "approval_key": self._connection_key,
                            "custtype": "P",
                            "tr_type": "2",  # 2: 구독 해제
                            "content-type": "utf-8"
                        },
                        "body": {
                            "input": {
                                "tr_id": data_type,
                                "tr_key": symbol
                            }
                        }
                    }
                    
                    # 구독 해제 요청 전송
                    await self._websocket.send(json.dumps(unsubscribe_msg))
                    
                    # 구독 목록에서 제거
                    subscription_key = f"{data_type}:{symbol}"
                    self._subscriptions.discard(subscription_key)
                    
                    logger.info(f"Unsubscribed from {symbol} - {data_type}")
                    
                except Exception as e:
                    logger.error(f"Unsubscribe failed for {symbol}: {e}")
                    return False
        
        return True
    
    async def _get_connection_key(self) -> None:
        """WebSocket 접속키 발급"""
        token = await self.auth_service.ensure_token()
        
        # 접속키 발급 API 호출
        headers = self.auth_service.get_headers(token)
        
        # TODO: 실제 접속키 발급 API 구현
        # 여기서는 임시로 토큰을 접속키로 사용
        self._connection_key = token.access_token
    
    async def _receive_loop(self) -> None:
        """메시지 수신 루프"""
        while self._running and self._websocket:
            try:
                message = await self._websocket.recv()
                
                # 메시지 파싱
                if isinstance(message, str):
                    data = json.loads(message)
                elif isinstance(message, bytes):
                    data = json.loads(message.decode('utf-8'))
                else:
                    continue
                
                # 메시지 타입별 처리
                await self._handle_message(data)
                
            except websockets.ConnectionClosed:
                logger.warning("WebSocket connection closed")
                self._connected = False
                await self._handle_reconnect()
                break
                
            except Exception as e:
                logger.error(f"Error in receive loop: {e}")
                if self.on_error:
                    self.on_error(str(e))
    
    async def _handle_message(self, data: Dict[str, Any]) -> None:
        """
        메시지 처리
        
        Args:
            data: 수신된 메시지 데이터
        """
        try:
            # 메시지 타입 확인
            header = data.get("header", {})
            body = data.get("body", {})
            
            tr_id = header.get("tr_id", "")
            
            # 핑퐁 응답
            if tr_id == "PINGPONG":
                self._last_ping_time = datetime.now()
                return
            
            # 에러 메시지
            if header.get("rsp_cd") != "0000":
                error_msg = header.get("rsp_msg", "Unknown error")
                logger.error(f"Server error: {error_msg}")
                if self.on_error:
                    self.on_error(error_msg)
                return
            
            # 실시간 데이터 처리
            if tr_id in ["H0STCNT0", "H0STCNI0"]:  # 호가, 체결
                realtime_data = self._parse_realtime_data(tr_id, body)
                if realtime_data and self.on_data:
                    self.on_data(realtime_data)
                    
        except Exception as e:
            logger.error(f"Error handling message: {e}")
    
    def _parse_realtime_data(self, tr_id: str, body: Dict[str, Any]) -> Optional[RealtimeData]:
        """
        실시간 데이터 파싱
        
        Args:
            tr_id: 거래ID
            body: 메시지 바디
        
        Returns:
            RealtimeData 객체
        """
        try:
            output = body.get("output", {})
            
            # 기본 정보
            realtime_data = RealtimeData(
                symbol=output.get("symb", ""),
                timestamp=datetime.now(),
                data_type=tr_id
            )
            
            # 호가 데이터
            if tr_id == "H0STCNT0":
                realtime_data.bid_price = Decimal(output.get("bidp", 0))
                realtime_data.bid_size = int(output.get("bidv", 0))
                realtime_data.ask_price = Decimal(output.get("askp", 0))
                realtime_data.ask_size = int(output.get("askv", 0))
            
            # 체결 데이터
            elif tr_id == "H0STCNI0":
                realtime_data.last_price = Decimal(output.get("last", 0))
                realtime_data.last_size = int(output.get("tvol", 0))
                realtime_data.volume = int(output.get("cvol", 0))
                realtime_data.change = Decimal(output.get("diff", 0))
                realtime_data.change_rate = Decimal(output.get("rate", 0))
            
            return realtime_data
            
        except Exception as e:
            logger.error(f"Failed to parse realtime data: {e}")
            return None
    
    async def _ping_loop(self) -> None:
        """핑퐁 메시지 전송 루프"""
        while self._running and self._websocket:
            try:
                # 30초마다 핑 전송
                await asyncio.sleep(30)
                
                ping_msg = {
                    "header": {
                        "tr_id": "PINGPONG"
                    }
                }
                
                await self._websocket.send(json.dumps(ping_msg))
                
            except Exception as e:
                logger.error(f"Ping failed: {e}")
                break
    
    async def _handle_reconnect(self) -> None:
        """재연결 처리"""
        if not self._running:
            return
        
        logger.info("Attempting to reconnect...")
        
        # 재연결 시도
        max_retries = 5
        retry_delay = 5
        
        for attempt in range(max_retries):
            await asyncio.sleep(retry_delay * (attempt + 1))
            
            if await self.connect():
                # 기존 구독 복원
                for subscription in list(self._subscriptions):
                    data_type, symbol = subscription.split(":")
                    await self.subscribe(symbol, [data_type])
                
                logger.info("Reconnection successful")
                return
        
        logger.error("Failed to reconnect after multiple attempts")
        if self.on_error:
            self.on_error("Connection lost and unable to reconnect")
