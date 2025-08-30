"""
KIS API 해외주식 주문 서비스
미국 주식 매수/매도/정정/취소 및 잔고 조회를 담당합니다.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

import httpx
from pydantic import BaseModel, Field
from tenacity import retry, stop_after_attempt, wait_exponential

from app.backend.core.config import settings
from app.backend.core.logging import get_logger, log_context
from app.backend.kis.auth import KISAuthService, get_auth_service
from app.backend.kis.hashkey import HashKeyService, get_hashkey_service

logger = get_logger(__name__)


class OrderSide(str, Enum):
    """주문 방향"""
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    """주문 유형"""
    LIMIT = "00"  # 지정가
    MARKET = "01"  # 시장가


class OrderResponse(BaseModel):
    """주문 응답 모델"""
    
    rt_cd: str = Field(..., description="응답코드")
    msg_cd: str = Field(..., description="메시지코드")
    msg1: str = Field(..., description="메시지")
    
    # 주문 성공 시 반환 정보
    odno: Optional[str] = Field(None, description="주문번호")
    ord_tmd: Optional[str] = Field(None, description="주문시각")
    
    @property
    def is_success(self) -> bool:
        """주문 성공 여부"""
        return self.rt_cd == "0"
    
    @property
    def error_message(self) -> str:
        """에러 메시지"""
        return self.msg1 if not self.is_success else ""


class Position(BaseModel):
    """포지션(잔고) 모델"""
    
    symbol: str = Field(..., description="종목코드")
    name: str = Field(..., description="종목명")
    quantity: int = Field(..., description="보유수량")
    avg_price: Decimal = Field(..., description="평균단가")
    current_price: Decimal = Field(..., description="현재가")
    eval_amount: Decimal = Field(..., description="평가금액")
    profit_loss: Decimal = Field(..., description="평가손익")
    profit_loss_rate: Decimal = Field(..., description="손익률")


class Execution(BaseModel):
    """체결 내역 모델"""
    
    order_id: str = Field(..., description="주문번호")
    symbol: str = Field(..., description="종목코드")
    side: OrderSide = Field(..., description="매매구분")
    executed_qty: int = Field(..., description="체결수량")
    executed_price: Decimal = Field(..., description="체결가격")
    executed_time: datetime = Field(..., description="체결시각")
    

class OverseasOrderApi:
    """
    해외주식 주문 API 클라이언트
    미국 주식 거래를 위한 주문/조회 기능을 제공합니다.
    """
    
    def __init__(
        self,
        auth_service: Optional[KISAuthService] = None,
        hashkey_service: Optional[HashKeyService] = None,
        account_no: Optional[str] = None,
        use_sandbox: Optional[bool] = None
    ):
        """
        Args:
            auth_service: 인증 서비스
            hashkey_service: HashKey 서비스
            account_no: 계좌번호
            use_sandbox: 모의투자 사용 여부
        """
        self.auth_service = auth_service
        self.hashkey_service = hashkey_service or get_hashkey_service()
        self.account_no = account_no or settings.kis_account_no
        self.use_sandbox = use_sandbox if use_sandbox is not None else settings.kis_use_sandbox
        self.base_url = settings.kis_base_url
        
        # 계좌번호 분리 (계좌번호-상품코드)
        parts = self.account_no.split("-")
        self.cano = parts[0] if len(parts) > 0 else ""  # 종합계좌번호
        self.acnt_prdt_cd = parts[1] if len(parts) > 1 else "01"  # 계좌상품코드
        
        # HTTP 클라이언트
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(30.0)
        )
    
    async def __aenter__(self):
        """비동기 컨텍스트 매니저 진입"""
        if not self.auth_service:
            self.auth_service = await get_auth_service()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """비동기 컨텍스트 매니저 종료"""
        await self._client.aclose()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def place_order(
        self,
        symbol: str,
        side: Literal["BUY", "SELL"],
        qty: int,
        price: Optional[float] = None,
        order_type: OrderType = OrderType.LIMIT,
        time_in_force: str = "IOC"  # IOC, FOK, GTD 등
    ) -> OrderResponse:
        """
        해외주식 주문
        
        Args:
            symbol: 종목코드 (예: "AAPL")
            side: 매매구분 (BUY/SELL)
            qty: 주문수량
            price: 주문가격 (시장가는 None)
            order_type: 주문유형 (지정가/시장가)
            time_in_force: 주문 유효기간
        
        Returns:
            OrderResponse 객체
        """
        # 토큰 확인
        token = await self.auth_service.ensure_token()
        
        # 주문 요청 바디 구성
        order_data = {
            "CANO": self.cano,
            "ACNT_PRDT_CD": self.acnt_prdt_cd,
            "OVRS_EXCG_CD": "NASD",  # 거래소코드 (NASD: 나스닥, NYSE: 뉴욕증권거래소)
            "PDNO": symbol,  # 종목코드
            "ORD_QTY": str(qty),  # 주문수량
            "OVRS_ORD_UNPR": str(price) if price else "0",  # 주문단가
            "ORD_SVR_DVSN_CD": "0",  # 주문서버구분 (0: 기본)
            "ORD_DVSN": order_type.value,  # 주문구분
        }
        
        # HashKey 생성
        hashkey = self.hashkey_service.sign_order(order_data)
        
        # 헤더 구성
        headers = self.auth_service.get_headers(token)
        headers["hashkey"] = hashkey
        
        # 거래ID 설정 (모의/실거래 구분)
        if self.use_sandbox:
            headers["tr_id"] = "VTTT1002U" if side == "BUY" else "VTTT1001U"  # 모의투자
        else:
            headers["tr_id"] = "TTTT1002U" if side == "BUY" else "TTTT1001U"  # 실거래
        
        logger.info(f"Placing {side} order", extra=log_context(
            symbol=symbol,
            qty=qty,
            price=price,
            order_type=order_type.value
        ))
        
        try:
            # API 요청
            endpoint = "/uapi/overseas-stock/v1/trading/order"
            response = await self._client.post(
                endpoint,
                headers=headers,
                json=order_data
            )
            response.raise_for_status()
            
            data = response.json()
            order_response = OrderResponse(**data)
            
            if order_response.is_success:
                logger.info(f"Order placed successfully", extra=log_context(
                    order_id=order_response.odno,
                    symbol=symbol,
                    side=side
                ))
            else:
                logger.error(f"Order failed", extra=log_context(
                    error=order_response.error_message,
                    symbol=symbol
                ))
            
            return order_response
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Order request failed: {e.response.status_code}", extra=log_context(
                status_code=e.response.status_code,
                response_body=e.response.text
            ))
            raise
        except Exception as e:
            logger.error(f"Unexpected error during order placement: {e}")
            raise
    
    async def cancel_order(
        self,
        order_id: str,
        symbol: str,
        qty: int
    ) -> OrderResponse:
        """
        주문 취소
        
        Args:
            order_id: 원주문번호
            symbol: 종목코드
            qty: 취소수량
        
        Returns:
            OrderResponse 객체
        """
        # 토큰 확인
        token = await self.auth_service.ensure_token()
        
        # 취소 요청 바디
        cancel_data = {
            "CANO": self.cano,
            "ACNT_PRDT_CD": self.acnt_prdt_cd,
            "OVRS_EXCG_CD": "NASD",
            "PDNO": symbol,
            "ORGN_ODNO": order_id,  # 원주문번호
            "RVSE_CNCL_DVSN_CD": "02",  # 02: 취소
            "ORD_QTY": str(qty),
        }
        
        # HashKey 생성
        hashkey = self.hashkey_service.sign_cancel(cancel_data)
        
        # 헤더 구성
        headers = self.auth_service.get_headers(token)
        headers["hashkey"] = hashkey
        headers["tr_id"] = "VTTT1004U" if self.use_sandbox else "TTTT1004U"
        
        logger.info(f"Canceling order", extra=log_context(
            order_id=order_id,
            symbol=symbol
        ))
        
        try:
            endpoint = "/uapi/overseas-stock/v1/trading/order-rvsecncl"
            response = await self._client.post(
                endpoint,
                headers=headers,
                json=cancel_data
            )
            response.raise_for_status()
            
            data = response.json()
            return OrderResponse(**data)
            
        except Exception as e:
            logger.error(f"Order cancellation failed: {e}")
            raise
    
    async def get_positions(self) -> List[Position]:
        """
        보유 잔고 조회
        
        Returns:
            Position 리스트
        """
        # 토큰 확인
        token = await self.auth_service.ensure_token()
        
        # 헤더 구성
        headers = self.auth_service.get_headers(token)
        headers["tr_id"] = "VTTC8001R" if self.use_sandbox else "TTTC8001R"
        
        # 쿼리 파라미터
        params = {
            "CANO": self.cano,
            "ACNT_PRDT_CD": self.acnt_prdt_cd,
            "OVRS_EXCG_CD": "NASD",
            "TR_CRCY_CD": "USD",
        }
        
        logger.info("Fetching positions")
        
        try:
            endpoint = "/uapi/overseas-stock/v1/trading/inquire-balance"
            response = await self._client.get(
                endpoint,
                headers=headers,
                params=params
            )
            response.raise_for_status()
            
            data = response.json()
            
            # 잔고 데이터 파싱
            positions = []
            if "output1" in data:
                for item in data["output1"]:
                    if int(item.get("ovrs_cblc_qty", 0)) > 0:  # 보유수량이 있는 경우만
                        position = Position(
                            symbol=item["ovrs_pdno"],
                            name=item["ovrs_item_name"],
                            quantity=int(item["ovrs_cblc_qty"]),
                            avg_price=Decimal(item["pchs_avg_pric"]),
                            current_price=Decimal(item["now_pric2"]),
                            eval_amount=Decimal(item["ovrs_stck_evlu_amt"]),
                            profit_loss=Decimal(item["frcr_evlu_pfls_amt"]),
                            profit_loss_rate=Decimal(item["evlu_pfls_rt"])
                        )
                        positions.append(position)
            
            logger.info(f"Found {len(positions)} positions")
            return positions
            
        except Exception as e:
            logger.error(f"Failed to fetch positions: {e}")
            raise
    
    async def get_executions(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        symbol: Optional[str] = None
    ) -> List[Execution]:
        """
        체결 내역 조회
        
        Args:
            start_date: 조회 시작일 (YYYYMMDD)
            end_date: 조회 종료일 (YYYYMMDD)
            symbol: 종목코드 (옵션)
        
        Returns:
            Execution 리스트
        """
        # 토큰 확인
        token = await self.auth_service.ensure_token()
        
        # 날짜 기본값 설정
        if not end_date:
            end_date = datetime.now().strftime("%Y%m%d")
        if not start_date:
            start_date = end_date
        
        # 헤더 구성
        headers = self.auth_service.get_headers(token)
        headers["tr_id"] = "VTTS3012R" if self.use_sandbox else "TTTS3012R"
        
        # 쿼리 파라미터
        params = {
            "CANO": self.cano,
            "ACNT_PRDT_CD": self.acnt_prdt_cd,
            "OVRS_EXCG_CD": "NASD",
            "SORT_SQN": "DS",  # 정렬순서 (DS: 내림차순)
            "CTX_AREA_FK200": "",
            "CTX_AREA_NK200": ""
        }
        
        if symbol:
            params["PDNO"] = symbol
        
        logger.info(f"Fetching executions from {start_date} to {end_date}")
        
        try:
            endpoint = "/uapi/overseas-stock/v1/trading/inquire-ccnl"
            response = await self._client.get(
                endpoint,
                headers=headers,
                params=params
            )
            response.raise_for_status()
            
            data = response.json()
            
            # 체결 데이터 파싱
            executions = []
            if "output" in data:
                for item in data["output"]:
                    execution = Execution(
                        order_id=item["odno"],
                        symbol=item["pdno"],
                        side=OrderSide.BUY if item["sll_buy_dvsn_cd"] == "02" else OrderSide.SELL,
                        executed_qty=int(item["ft_ccld_qty"]),
                        executed_price=Decimal(item["ft_ccld_unpr3"]),
                        executed_time=datetime.strptime(
                            f"{item['dmst_ord_dt']} {item['ft_ccld_tmd']}",
                            "%Y%m%d %H%M%S"
                        )
                    )
                    executions.append(execution)
            
            logger.info(f"Found {len(executions)} executions")
            return executions
            
        except Exception as e:
            logger.error(f"Failed to fetch executions: {e}")
            raise
    
    async def get_account_balance(self) -> Dict[str, Any]:
        """
        계좌 잔고 및 예수금 조회
        
        Returns:
            계좌 잔고 정보
        """
        # 토큰 확인
        token = await self.auth_service.ensure_token()
        
        # 헤더 구성
        headers = self.auth_service.get_headers(token)
        headers["tr_id"] = "VTRP6504R" if self.use_sandbox else "TTRP6504R"
        
        # 쿼리 파라미터
        params = {
            "CANO": self.cano,
            "ACNT_PRDT_CD": self.acnt_prdt_cd,
            "OVRS_EXCG_CD": "NASD",
            "OVRS_ORD_UNPR": "0",
            "ITEM_CD": ""
        }
        
        try:
            endpoint = "/uapi/overseas-stock/v1/trading/inquire-psamount"
            response = await self._client.get(
                endpoint,
                headers=headers,
                params=params
            )
            response.raise_for_status()
            
            data = response.json()
            
            # 잔고 정보 추출
            if "output" in data:
                output = data["output"]
                return {
                    "total_balance": Decimal(output.get("tot_evlu_pfls_amt", 0)),
                    "cash_balance": Decimal(output.get("frcr_dncl_amt_2", 0)),
                    "available_cash": Decimal(output.get("frcr_buy_mgn_amt", 0)),
                    "total_profit_loss": Decimal(output.get("ovrs_tot_pfls", 0)),
                    "profit_loss_rate": Decimal(output.get("tot_pftrt", 0))
                }
            
            return {}
            
        except Exception as e:
            logger.error(f"Failed to fetch account balance: {e}")
            raise
