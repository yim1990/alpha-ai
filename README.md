# Alpha AI Trading System 🚀

한국투자증권(KIS) Open API를 활용한 미국 주식 자동매매 시스템

## 📋 프로젝트 개요

Alpha AI는 한국투자증권 Open API를 통해 미국 주식을 자동으로 거래하는 시스템입니다. 웹 기반 관리자 인터페이스에서 다중 계좌와 매매 규칙을 관리하고, 각 계좌는 별도의 백그라운드 프로세스로 규칙에 따라 자동 매수/매도를 수행합니다.

### 주요 기능

- 🏦 **다중 계좌 관리**: 여러 KIS 계좌를 동시에 관리
- 📊 **자동매매 규칙**: JSON/YAML 기반 매매 전략 설정
- 🔐 **보안**: API 자격증명 암호화 저장 (AES-256-GCM)
- 📈 **실시간 모니터링**: WebSocket을 통한 실시간 시세 및 체결 정보
- 🎯 **리스크 관리**: 포지션 한도, 손절/익절, 쿨다운 설정
- 📝 **감사 로그**: 모든 거래 활동 기록

## 🛠 기술 스택

### Backend
- **Python 3.12** + **FastAPI** (비동기 REST API)
- **SQLAlchemy 2.0** + **Alembic** (ORM 및 마이그레이션)
- **Celery** + **Redis** (백그라운드 작업 및 스케줄링)
- **Supabase** (PostgreSQL 데이터베이스)

### Frontend
- **Next.js 14** (App Router)
- **TypeScript**
- **Tailwind CSS** (스타일링)
- **NextAuth** (인증)

### Infrastructure
- **Docker** + **Docker Compose**
- **GitHub Actions** (CI/CD)

## 📦 프로젝트 구조

```
alpha-ai/
├── app/
│   ├── backend/
│   │   ├── kis/           # KIS API 클라이언트
│   │   ├── core/          # 핵심 설정 및 유틸리티
│   │   ├── models/        # SQLAlchemy ORM 모델
│   │   ├── schemas/       # Pydantic 스키마
│   │   ├── services/      # 비즈니스 로직
│   │   ├── routes/        # FastAPI 라우트
│   │   ├── workers/       # Celery 태스크
│   │   └── main.py        # FastAPI 앱
│   └── frontend/
│       ├── app/           # Next.js App Router
│       ├── components/    # React 컴포넌트
│       └── lib/           # 유틸리티
├── infra/
│   ├── migrations/        # Alembic 마이그레이션
│   └── Dockerfile.*       # Docker 설정
├── tests/
└── docker-compose.yml
```

## 🚀 시작하기

### 사전 요구사항

1. **Docker** 및 **Docker Compose** 설치
2. **한국투자증권 Open API** 계정 및 API 키
3. **Supabase** 프로젝트 (또는 로컬 PostgreSQL)

### 환경 설정

1. 환경 변수 파일 생성:
```bash
cp env.example .env
```

2. `.env` 파일 수정:
```env
# KIS API 설정
KIS_APP_KEY=your_app_key_here
KIS_APP_SECRET=your_app_secret_here
KIS_ACCOUNT_NO=your_account_number_here
KIS_USE_SANDBOX=true  # 모의투자 사용

# Supabase 설정
SUPABASE_DB_URL=postgresql+psycopg://user:password@host:port/database
SUPABASE_PROJECT_URL=https://xxxxx.supabase.co
SUPABASE_ANON_KEY=your_anon_key_here

# 보안 키 (32바이트 문자열로 변경)
ENCRYPTION_KEY=change_this_32_byte_key_in_prod!
```

### 실행 방법

#### 1. Docker Compose로 전체 시스템 실행

```bash
# 서비스 시작
docker-compose up -d

# 로그 확인
docker-compose logs -f

# 서비스 중지
docker-compose down
```

#### 2. 개발 환경 실행

```bash
# Poetry 설치 (Python 패키지 관리)
pip install poetry

# 백엔드 의존성 설치
poetry install

# 데이터베이스 마이그레이션
poetry run alembic upgrade head

# 백엔드 서버 실행
poetry run uvicorn app.backend.main:app --reload

# 새 터미널에서 Celery Worker 실행
poetry run celery -A app.backend.celery_app worker --loglevel=info

# 새 터미널에서 Celery Beat 실행
poetry run celery -A app.backend.celery_app beat --loglevel=info
```

프론트엔드 실행:
```bash
cd app/frontend
npm install
npm run dev
```

### 접속 URL

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API 문서**: http://localhost:8000/api/docs
- **Flower (Celery 모니터링)**: http://localhost:5555

## 📝 사용 방법

### 1. 계좌 등록

1. 관리자 페이지 접속 (http://localhost:3000)
2. "계좌 관리" 메뉴 클릭
3. "새 계좌 추가" 버튼 클릭
4. KIS API 자격증명 입력 (암호화되어 저장됨)

### 2. 매매 규칙 설정

1. "규칙 관리" 메뉴 클릭
2. "새 규칙 추가" 버튼 클릭
3. 매매 조건 설정:
   - 종목 코드 (예: AAPL, MSFT)
   - 매수 금액
   - 진입/청산 조건
   - 리스크 관리 설정

### 3. 자동매매 시작

1. 계좌 목록에서 "활성화" 토글 ON
2. 규칙 목록에서 원하는 규칙 "활성화"
3. 대시보드에서 실시간 거래 현황 모니터링

## ⚠️ 주의사항

### 모의투자 vs 실거래

- **반드시 모의투자로 먼저 테스트** 후 실거래 전환
- `KIS_USE_SANDBOX=true` 설정으로 모의투자 사용
- 실거래 전환 시 충분한 테스트 필수

### 보안

- API 키와 계좌번호는 절대 외부에 노출하지 마세요
- `.env` 파일은 Git에 커밋하지 마세요
- 프로덕션 환경에서는 강력한 암호화 키 사용
- HTTPS 사용 권장

### API 제한

- KIS API 호출 한도 확인 (분당 20회 등)
- 레이트 리밋 초과 시 자동 재시도 로직 포함
- 토큰 만료 전 자동 갱신

## 🧪 테스트

```bash
# 단위 테스트 실행
poetry run pytest tests/

# 커버리지 확인
poetry run pytest --cov=app tests/

# E2E 테스트
poetry run pytest tests/e2e/
```

## 📊 모니터링

### 로그 확인

```bash
# 백엔드 로그
docker-compose logs -f backend

# Celery Worker 로그
docker-compose logs -f celery-worker

# 전체 로그
docker-compose logs -f
```

### Flower (Celery 모니터링)

http://localhost:5555 접속하여 Celery 작업 상태 확인

## 🤝 기여하기

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 라이선스

이 프로젝트는 MIT 라이선스를 따릅니다.

## ⚖️ 면책 조항

**이 소프트웨어는 교육 및 연구 목적으로 제공됩니다. 실제 투자에 사용할 경우 발생하는 모든 손실에 대해 개발자는 책임지지 않습니다. 투자는 본인의 판단과 책임 하에 진행하시기 바랍니다.**

## 📞 문의

- Email: jasonim@wingeat.com
- GitHub: [@jasonim](https://github.com/jasonim)

---

Made with ❤️ by Jason Im
