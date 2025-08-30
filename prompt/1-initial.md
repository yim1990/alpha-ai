프로젝트 목표: 한국투자증권(KIS) Open API로 미국 주식 자동매매 시스템을 개발한다.
웹 어드민에서 다중 계정과 매매 규칙을 관리하고, 각 계좌는 별도 백그라운드 프로세스로 규칙에 따라 자동 매수/매도를 수행한다.

중요: KIS Open API의 인증 토큰 발급/갱신, HashKey 서명, 해외주식 주문·계좌, 토큰 만료/오류 코드/레이트리밋 재시도 포함.

⸻

기술 스택
	•	Backend: Python 3.12, FastAPI(async), uvicorn
	•	Workers: Celery + Redis, Celery Beat(스케줄)
	•	Database: Supabase(PostgreSQL)
	•	SQLAlchemy 2 + Alembic(마이그레이션)
	•	서버 사이드에서 Supabase DB URL로 연결(ORM 사용), 민감 정보는 암호화 저장
	•	Frontend(Admin): Next.js 14(App Router) + TypeScript + Tailwind CSS
	•	UI 빌딩은 Tailwind 유틸리티 클래스 중심(컴포넌트 라이브러리는 최소화/선택)
	•	Realtime: Backend→Admin SSE(로그/주문/포지션 스트림), KIS 시세/체결은 KIS WebSocket
	•	Auth(Admin): NextAuth(이메일/비번 또는 OAuth) + RBAC(Admin/Trader/Viewer)
	•	Secrets: python-dotenv(로컬), 프로덕션은 클라우드 Secrets Manager 훅만 마련
	•	Quality/CI: pytest, Ruff/Black, pre-commit, GitHub Actions(테스트/빌드)

⸻

모놀리포 구조

/app
  /backend
    /kis/              # KIS API 클라이언트 (REST/WebSocket, auth, hashkey)
    /core/             # 설정, 로깅, 보안, 의존성
    /models/           # SQLAlchemy ORM
    /schemas/          # Pydantic 스키마
    /services/         # 주문/규칙평가/리스크/포지션
    /routes/           # FastAPI 라우트 (accounts, rules, orders, bots, logs)
    /workers/          # Celery tasks (계좌 봇, 스케줄러)
    /backtests/        # 전략 리플레이/시뮬
    main.py
    celery_app.py
  /frontend
    /app/(admin)       # Next.js App Router 페이지
    /components        # Tailwind 기반 UI
    /lib
    /styles
  /infra
    docker-compose.yml
    alembic.ini
  /tests
    /backend /e2e


⸻

데이터 모델
	•	User(id, email, role)
	•	BrokerageAccount(id, user_id, nickname, broker=‘KIS’, market=‘US’, enabled, health_status, last_heartbeat)
	•	ApiCredential(id, account_id, app_key(enc), app_secret(enc), account_no(enc), sandbox:bool, access_token(enc), token_expire_at)
	•	TradeRule(id, account_id, symbol, buy_amount_usd, max_position, entry_condition(json/yaml), exit_condition(json/yaml), time_in_force, cooldown_sec, enabled)
	•	Order(id, account_id, rule_id, side, qty, price, status, broker_order_id, placed_at, filled_qty, avg_fill_price, raw(json))
	•	Position(id, account_id, symbol, qty, avg_price, unrealized_pnl, updated_at)
	•	ExecutionLog(id, account_id, rule_id?, level, message, ctx(json), created_at)
	•	StrategySignal(id, rule_id, type(ENTRY|EXIT), score, payload, created_at)

⸻

백엔드 요구사항
	1.	KIS API 클라이언트(kis/)
	•	AuthService: 클라이언트 크레덴셜로 Access Token 발급/갱신, 만료 임박 자동 갱신
	•	HashKeyService: 주문 요청 바디에 대한 HashKey 생성
	•	OverseasOrderApi: 해외주식 주문/정정/취소, 잔고/예수금/체결/미체결 조회
	•	RealtimeClient: 실시간 WebSocket 접속키 발급 → 호가/체결 구독/해제, 끊김 감지 재연결
	•	모든 요청/응답의 구조화 로깅, 레이트리밋/5xx 백오프 재시도
	2.	전략/규칙 엔진(services/)
	•	규칙 표현: DSL(JSON/YAML) 또는 Python 콜러블(샌드박스 실행) 2가지 모드 지원
	•	리스크 가드: (1) 일일 총매수액/종목당 최대보유 (2) 슬리피지·호가단위 검증 (3) 거래 가능 시간(KST 기준 미국장/프리·애프터) (4) 연속 실패 쿨다운
	•	주문 라우팅: 조건 충족 → 수량/금액 산출 → HashKey 서명 → 주문 전송 → 체결 추적/미체결 정리
	3.	봇/워커(workers/)
	•	계좌별 Celery Task 루프
	•	토큰 보장 → 실시간/폴백 데이터 수집 → 규칙 평가 → 주문 → 포지션 업데이트
	•	예외 격리, 헬스비트 기록, 재시작 안전성(아이들포인트 저장)
	•	스케줄러: 장 시작/마감 훅, 정기 리밸런싱, 미체결 청산 정책
	4.	API 라우트(routes/)
	•	POST /accounts / GET /accounts / PATCH /accounts/{id} / POST /accounts/{id}:toggle
	•	POST /accounts/{id}/credentials(암호화 저장/갱신)
	•	POST /rules / GET /rules?account_id= / PATCH /rules/{id} / POST /rules/{id}:toggle
	•	GET /orders / POST /orders/{id}:cancel
	•	GET /positions?account_id=
	•	GET /logs?account_id=&rule_id=&level=  → SSE로 실시간 로그 스트림
	•	POST /webhook/tradingview (옵션)
	•	모든 변경은 감사 로그 남기기
	5.	보안/컴플라이언스
	•	자격증명/토큰/계좌번호 등은 AES-GCM 등으로 암호화해 DB 저장(키는 환경변수→KMS 전환 지점 마련)
	•	응답 마스킹, 입력 검증, RBAC, 관리 작업 이중 확인 모달
	6.	관측성
	•	구조화 로그(JSON), 주문성공률/체결지연/전략별 PnL/에러율 메트릭 노출(추후 OTLP 연동 가능)
	7.	테스트
	•	단위: KIS 클라이언트 모킹, 규칙 평가, 리스크 가드
	•	통합: 모의투자 엔드포인트로 주문 플로우
	•	회귀: 과거 데이터 리플레이(간이 백테스트)

⸻

프론트(어드민) 요구사항 — Tailwind CSS
	•	페이지: 대시보드(계좌 상태·PnL·오더 피드), 계정/자격증명, 규칙/전략 CRUD, 주문/체결, 실시간 로그(SSE)
	•	Tailwind만으로 레이아웃/컴포넌트 구성(카드, 테이블, 모달, 토글, 폼)
	•	Zod로 폼 유효성, TanStack Query로 데이터 패칭/캐싱
	•	위험 작업(실거래 전환/규칙 활성화)은 이중 확인 모달 + “타이핑 확인(계좌명 입력)”

⸻

환경 변수(.env 예시)

# Supabase (DB/선택적 API)
SUPABASE_DB_URL=postgresql+psycopg://USER:PASSWORD@HOST:PORT/postgres
SUPABASE_PROJECT_URL=https://xxxxx.supabase.co
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...     # 백엔드 전용(필요 시)

# Redis / Workers
REDIS_URL=redis://localhost:6379/0

# KIS
KIS_APP_KEY=...
KIS_APP_SECRET=...
KIS_ACCOUNT_NO=...                # 끝 2자리 상품코드 유의
KIS_USE_SANDBOX=true

# Admin Auth
NEXTAUTH_SECRET=...
NEXTAUTH_URL=http://localhost:3000


⸻

우선 구현 순서(생성 지시)
	1.	위 폴더 구조로 백엔드/프론트 템플릿과 Docker Compose 생성
	2.	KIS Auth/HashKey/Orders/WebSocket 스텁 및 샘플 구현(모의투자 우선)
	3.	Supabase(Postgres) 연결, ORM 모델/마이그레이션, 기본 CRUD 라우트, SSE 로그 엔드포인트
	4.	Celery 워커: 계좌별 봇 루프(토큰 관리 → 규칙 평가 → 주문)
	5.	어드민 UI(Tailwind): 계정·자격증명·규칙 CRUD, 대시보드·로그 스트림
	6.	모의투자 E2E 시나리오 및 테스트 파이프라인

⸻

샘플 시그니처
	•	kis/auth.py
	•	async def get_access_token() -> AccessToken
	•	async def ensure_token() -> AccessToken  # 만료 임박 시 재발급
	•	kis/hashkey.py
	•	def sign_order(payload: dict) -> str
	•	kis/overseas_orders.py
	•	async def place_order(symbol: str, side: Literal["BUY","SELL"], qty: int, price: float | None, ...) -> OrderResponse
	•	async def get_positions() -> list[Position]
	•	async def get_executions(...) -> list[Execution]
	•	kis/realtime.py
	•	class RealtimeClient: async connect(); async subscribe(symbol); on_tick(callback)
	•	services/rules.py
	•	def evaluate(rule: TradeRule, market: MarketData) -> Decision
	•	workers/bot.py
	•	@celery.task def run_account_bot(account_id: UUID)

⸻

오류/만료/복구 지침
	•	Access Token 만료/폐기 자동 재발급, 429/5xx 지수 백오프 재시도
	•	주문 전 HashKey 필수, 오류코드 → 사용자 친화 메시지 맵핑
	•	실시간 WebSocket 끊김 감지 → 재연결 + 구독 재수립
	•	워커 장애 시 아이들포인트 체크포인트로 안전 재기동

⸻

산출물(최소기능)
	•	계정/자격증명 등록(암호화 저장) → 규칙 생성 → 계좌 봇 활성화 → 모의투자 주문 발생
	•	어드민에서 주문/포지션/로그 실시간 확인
	•	README: Supabase 연결/KIS 키 발급/모의투자 사용법/주의사항