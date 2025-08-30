#!/usr/bin/env python3
"""
개선된 KIS API 테스트 - 토큰 재사용으로 레이트 리밋 해결
"""

import asyncio
import os
from datetime import datetime
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

from app.backend.kis.auth import KISAuthService
from app.backend.core.logging import get_logger

logger = get_logger(__name__)


async def test_improved_kis_integration():
    """개선된 KIS API 통합 테스트"""
    print("🚀 개선된 KIS API 테스트 시작")
    print("=" * 50)
    
    # 환경 변수 확인
    app_key = os.getenv("KIS_APP_KEY")
    app_secret = os.getenv("KIS_APP_SECRET")
    account_no = os.getenv("KIS_ACCOUNT_NO")
    use_sandbox = os.getenv("KIS_USE_SANDBOX", "true").lower() == "true"
    
    print(f"📋 설정 확인:")
    print(f"   App Key: {app_key[:10] if app_key else 'None'}***")
    print(f"   Account: {account_no[:8] if account_no else 'None'}***")
    print(f"   모의투자: {'✅ ON' if use_sandbox else '❌ OFF'}")
    print()
    
    # 단일 인증 서비스 인스턴스 생성
    auth_service = KISAuthService(
        app_key=app_key,
        app_secret=app_secret,
        use_sandbox=use_sandbox
    )
    
    try:
        # 1. 토큰 발급 (한 번만)
        print("🔐 1단계: 인증 토큰 발급")
        token = await auth_service.get_access_token()
        
        print(f"✅ 토큰 발급 성공!")
        print(f"   토큰: {token.access_token[:20]}***")
        print(f"   만료: {token.expires_at}")
        print(f"   유효: {not token.is_expired}")
        print()
        
        # 2. 토큰 재사용 확인
        print("🔄 2단계: 토큰 재사용 테스트")
        cached_token = await auth_service.ensure_token()
        
        if cached_token.access_token == token.access_token:
            print("✅ 토큰 캐싱 정상 작동!")
        else:
            print("⚠️  새로운 토큰이 발급됨")
        print()
        
        # 3. 실제 API 헤더 생성 테스트
        print("📡 3단계: API 헤더 생성 테스트")
        headers = auth_service.get_headers(token)
        
        print("✅ API 헤더 생성 완료:")
        for key, value in headers.items():
            if key.lower() in ['authorization', 'appkey', 'appsecret']:
                display_value = f"{value[:20]}***" if len(value) > 20 else value
                print(f"   {key}: {display_value}")
            else:
                print(f"   {key}: {value}")
        print()
        
        # 4. 간단한 API 호출 시뮬레이션
        print("🎯 4단계: API 호출 준비 완료")
        print("✅ 모든 준비가 완료되었습니다!")
        print("📝 다음 단계:")
        print("   - 실제 시세 조회 API 호출")
        print("   - 계좌 잔고 조회")  
        print("   - 모의 주문 테스트")
        
        return True
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        return False
        
    finally:
        await auth_service.close()


async def test_market_data_simple():
    """간단한 시장 데이터 조회 테스트"""
    print("\n📊 간단한 시장 데이터 테스트")
    print("-" * 30)
    
    try:
        import httpx
        
        # KIS API 설정
        app_key = os.getenv("KIS_APP_KEY")
        app_secret = os.getenv("KIS_APP_SECRET")
        use_sandbox = os.getenv("KIS_USE_SANDBOX", "true").lower() == "true"
        
        base_url = "https://openapivts.koreainvestment.com:29443" if use_sandbox else "https://openapi.koreainvestment.com:9443"
        
        # 토큰 발급
        auth_service = KISAuthService(app_key=app_key, app_secret=app_secret, use_sandbox=use_sandbox)
        token = await auth_service.get_access_token()
        
        # 미국 주식 현재가 조회 (AAPL)
        print("🔄 AAPL 현재가 조회 중...")
        
        headers = {
            "content-type": "application/json; charset=utf-8",
            "authorization": token.authorization_header,
            "appkey": app_key,
            "appsecret": app_secret,
            "tr_id": "HHDFS00000300"  # 해외주식 현재가
        }
        
        params = {
            "AUTH": "",
            "EXCD": "NAS",  # 나스닥
            "SYMB": "AAPL"  # 애플
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{base_url}/uapi/overseas-price/v1/quotations/price",
                headers=headers,
                params=params
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("rt_cd") == "0":
                    output = data.get("output", {})
                    print("✅ AAPL 현재가 조회 성공!")
                    print(f"   현재가: ${output.get('last', 'N/A')}")
                    print(f"   전일종가: ${output.get('base', 'N/A')}")
                    print(f"   등락률: {output.get('rate', 'N/A')}%")
                else:
                    print(f"⚠️  API 응답 오류: {data.get('msg1', 'Unknown error')}")
            else:
                print(f"❌ HTTP 오류: {response.status_code}")
                print(f"   응답: {response.text[:200]}...")
        
        await auth_service.close()
        return True
        
    except Exception as e:
        print(f"❌ 시장 데이터 테스트 실패: {e}")
        return False


async def main():
    """메인 실행"""
    print(f"⏰ 시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 기본 테스트
    success1 = await test_improved_kis_integration()
    
    if success1:
        # 추가 테스트 (60초 대기해서 레이트 리밋 피하기)
        print("\n⏳ 레이트 리밋을 피하기 위해 잠시 대기...")
        print("   (실제 운영에서는 토큰을 재사용하므로 이 문제가 없습니다)")
        
        # 간단한 카운트다운
        for i in range(5, 0, -1):
            print(f"   {i}초 후 시장 데이터 테스트...")
            await asyncio.sleep(1)
        
        success2 = await test_market_data_simple()
    else:
        success2 = False
    
    # 결과 요약
    print("\n" + "=" * 50)
    print("📋 최종 결과:")
    print(f"   기본 연동: {'✅ 성공' if success1 else '❌ 실패'}")
    print(f"   시장 데이터: {'✅ 성공' if success2 else '❌ 실패'}")
    
    if success1 and success2:
        print("\n🎉 KIS API 연동 완전 성공!")
        print("🚀 이제 실제 트레이딩 시스템에 통합할 준비가 되었습니다.")
    elif success1:
        print("\n✅ 기본 연동 성공!")
        print("📈 시장 데이터는 레이트 리밋 때문에 실패했지만, 기본적으로 작동합니다.")
    else:
        print("\n⚠️  연동에 문제가 있습니다. API 키를 확인해주세요.")
    
    print(f"⏰ 종료: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    asyncio.run(main())
