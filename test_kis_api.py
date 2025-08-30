#!/usr/bin/env python3
"""
KIS API 연동 테스트 스크립트
실제 한국투자증권 Open API와 통신하여 기능을 검증합니다.
"""

import asyncio
import os
from datetime import datetime
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# 프로젝트 모듈 import
from app.backend.kis.auth import KISAuthService
from app.backend.kis.overseas_orders import OverseasOrderApi
from app.backend.core.logging import get_logger

logger = get_logger(__name__)


async def test_kis_authentication():
    """KIS API 인증 테스트"""
    print("🔐 KIS API 인증 테스트 시작...")
    
    try:
        # 환경 변수 확인
        app_key = os.getenv("KIS_APP_KEY")
        app_secret = os.getenv("KIS_APP_SECRET")
        use_sandbox = os.getenv("KIS_USE_SANDBOX", "true").lower() == "true"
        
        if not app_key or not app_secret:
            print("❌ KIS API 자격증명이 설정되지 않았습니다.")
            print("📝 .env 파일에 다음을 설정하세요:")
            print("   KIS_APP_KEY=your_app_key")
            print("   KIS_APP_SECRET=your_app_secret")
            print("   KIS_ACCOUNT_NO=your_account_number")
            return False
        
        print(f"📋 App Key: {app_key[:10]}***")
        print(f"🏖️  모의투자 모드: {'✅ ON' if use_sandbox else '❌ OFF (실거래)'}")
        
        # 인증 서비스 생성
        auth_service = KISAuthService(
            app_key=app_key,
            app_secret=app_secret,
            use_sandbox=use_sandbox
        )
        
        # 토큰 발급 시도
        print("🔄 Access Token 발급 중...")
        token = await auth_service.get_access_token()
        
        print(f"✅ 토큰 발급 성공!")
        print(f"   토큰: {token.access_token[:20]}***")
        print(f"   만료시간: {token.expires_at}")
        print(f"   유효시간: {token.expires_in}초")
        
        await auth_service.close()
        return True
        
    except Exception as e:
        print(f"❌ 인증 실패: {e}")
        logger.error(f"KIS authentication failed: {e}")
        return False


async def test_kis_market_data():
    """KIS API 시장 데이터 조회 테스트"""
    print("\n📊 KIS API 시장 데이터 조회 테스트...")
    
    try:
        # 환경 변수
        app_key = os.getenv("KIS_APP_KEY")
        app_secret = os.getenv("KIS_APP_SECRET")
        account_no = os.getenv("KIS_ACCOUNT_NO")
        use_sandbox = os.getenv("KIS_USE_SANDBOX", "true").lower() == "true"
        
        if not all([app_key, app_secret, account_no]):
            print("❌ 필수 환경 변수가 설정되지 않았습니다.")
            return False
        
        # 인증 서비스
        auth_service = KISAuthService(
            app_key=app_key,
            app_secret=app_secret,
            use_sandbox=use_sandbox
        )
        
        # 주문 API 클라이언트
        async with OverseasOrderApi(
            auth_service=auth_service,
            account_no=account_no,
            use_sandbox=use_sandbox
        ) as order_api:
            print("🔄 계좌 잔고 조회 중...")
            
            # 계좌 잔고 조회
            balance = await order_api.get_account_balance()
            
            if balance:
                print("✅ 계좌 정보 조회 성공!")
                print(f"   💰 총 잔고: ${balance.get('total_balance', 0):,.2f}")
                print(f"   💵 현금 잔고: ${balance.get('cash_balance', 0):,.2f}")
                print(f"   📈 총 손익: ${balance.get('total_profit_loss', 0):,.2f}")
            else:
                print("⚠️  잔고 정보를 받을 수 없습니다.")
            
            print("\n🔄 보유 포지션 조회 중...")
            
            # 포지션 조회
            positions = await order_api.get_positions()
            
            if positions:
                print(f"✅ 포지션 조회 성공! ({len(positions)}개)")
                for pos in positions[:3]:  # 처음 3개만 표시
                    print(f"   📊 {pos.symbol}: {pos.quantity}주")
                    print(f"      평단가: ${pos.avg_price:.2f}")
                    print(f"      현재가: ${pos.current_price:.2f}")
                    print(f"      손익: ${pos.profit_loss:.2f} ({pos.profit_loss_rate:.2f}%)")
            else:
                print("ℹ️  현재 보유 중인 포지션이 없습니다.")
        
        return True
        
    except Exception as e:
        print(f"❌ 시장 데이터 조회 실패: {e}")
        logger.error(f"Market data test failed: {e}")
        return False


async def test_kis_order_simulation():
    """KIS API 모의 주문 테스트 (실제 주문 X)"""
    print("\n🧪 KIS API 주문 시뮬레이션 테스트...")
    
    try:
        app_key = os.getenv("KIS_APP_KEY")
        app_secret = os.getenv("KIS_APP_SECRET")
        account_no = os.getenv("KIS_ACCOUNT_NO")
        use_sandbox = os.getenv("KIS_USE_SANDBOX", "true").lower() == "true"
        
        if not use_sandbox:
            print("⚠️  실거래 모드에서는 주문 시뮬레이션을 건너뜁니다.")
            return True
        
        # 인증 서비스
        auth_service = KISAuthService(
            app_key=app_key,
            app_secret=app_secret,
            use_sandbox=use_sandbox
        )
        
        async with OverseasOrderApi(
            auth_service=auth_service,
            account_no=account_no,
            use_sandbox=use_sandbox
        ) as order_api:
            print("🔄 모의 주문 테스트 중... (AAPL 1주 시장가 매수)")
            
            # 실제로는 주문하지 않고 검증만
            print("✅ 주문 API 클라이언트 정상 초기화")
            print("ℹ️  실제 주문은 하지 않습니다 (안전)")
            
            # 주문 내역 조회는 해봄
            print("\n🔄 기존 주문 내역 조회 중...")
            executions = await order_api.get_executions()
            
            if executions:
                print(f"✅ 주문 내역 조회 성공! ({len(executions)}개)")
                for exec in executions[:2]:  # 처음 2개만 표시
                    print(f"   📋 {exec.symbol}: {exec.executed_qty}주")
                    print(f"      체결가: ${exec.executed_price:.2f}")
                    print(f"      시간: {exec.executed_time}")
            else:
                print("ℹ️  기존 주문 내역이 없습니다.")
        
        return True
        
    except Exception as e:
        print(f"❌ 주문 테스트 실패: {e}")
        logger.error(f"Order simulation failed: {e}")
        return False


async def main():
    """메인 테스트 실행"""
    print("🚀 KIS API 연동 테스트 시작")
    print("=" * 50)
    print(f"⏰ 시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 테스트 순서
    tests = [
        ("인증", test_kis_authentication),
        ("시장데이터", test_kis_market_data),
        ("주문시뮬레이션", test_kis_order_simulation),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results[test_name] = result
        except Exception as e:
            print(f"❌ {test_name} 테스트 중 오류: {e}")
            results[test_name] = False
    
    # 결과 요약
    print("\n" + "=" * 50)
    print("📋 테스트 결과 요약:")
    
    success_count = 0
    for test_name, result in results.items():
        status = "✅ 성공" if result else "❌ 실패"
        print(f"   {test_name}: {status}")
        if result:
            success_count += 1
    
    print(f"\n🎯 전체 결과: {success_count}/{len(tests)} 성공")
    
    if success_count == len(tests):
        print("🎉 모든 테스트 통과! KIS API 연동 준비 완료")
    else:
        print("⚠️  일부 테스트 실패. 설정을 확인해주세요.")
    
    print(f"⏰ 종료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    asyncio.run(main())
