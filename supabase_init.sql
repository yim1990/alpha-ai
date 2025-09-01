-- =============================================
-- Alpha AI Trading System - Database Initialization
-- =============================================
-- 이 스크립트를 Supabase SQL 에디터에서 실행하세요

-- 1. ENUM 타입들 생성
-- =============================================

-- 사용자 역할
CREATE TYPE userrole AS ENUM ('ADMIN', 'TRADER', 'VIEWER');

-- 브로커 타입
CREATE TYPE brokertype AS ENUM ('KIS');

-- 시장 타입  
CREATE TYPE markettype AS ENUM ('US', 'KR');

-- 계좌 상태
CREATE TYPE accounthealthstatus AS ENUM ('HEALTHY', 'WARNING', 'ERROR', 'INACTIVE');

-- 주문 방향
CREATE TYPE orderside AS ENUM ('BUY', 'SELL');

-- 주문 상태
CREATE TYPE orderstatus AS ENUM ('PENDING', 'PLACED', 'PARTIALLY_FILLED', 'FILLED', 'CANCELLED', 'REJECTED', 'FAILED');

-- 로그 레벨
CREATE TYPE loglevel AS ENUM ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL');

-- 시그널 타입
CREATE TYPE signaltype AS ENUM ('ENTRY', 'EXIT', 'HOLD', 'NEUTRAL');

-- 2. 사용자 테이블
-- =============================================
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(100) NOT NULL,
    role userrole DEFAULT 'VIEWER' NOT NULL,
    is_active BOOLEAN DEFAULT true NOT NULL,
    is_verified BOOLEAN DEFAULT false NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    last_login_at TIMESTAMP WITH TIME ZONE
);

-- 3. 증권 계좌 테이블
-- =============================================
CREATE TABLE brokerage_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    nickname VARCHAR(100) NOT NULL,
    broker brokertype DEFAULT 'KIS' NOT NULL,
    market markettype DEFAULT 'US' NOT NULL,
    enabled BOOLEAN DEFAULT false NOT NULL,
    health_status accounthealthstatus DEFAULT 'INACTIVE' NOT NULL,
    last_heartbeat TIMESTAMP WITH TIME ZONE,
    config TEXT, -- JSON 형식의 추가 설정
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- 4. API 자격증명 테이블
-- =============================================
CREATE TABLE api_credentials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID NOT NULL REFERENCES brokerage_accounts(id) ON DELETE CASCADE,
    app_key_encrypted TEXT NOT NULL, -- 암호화된 App Key
    app_secret_encrypted TEXT NOT NULL, -- 암호화된 App Secret
    account_no_encrypted TEXT NOT NULL, -- 암호화된 계좌번호
    sandbox BOOLEAN DEFAULT true NOT NULL, -- 모의투자 여부
    access_token_encrypted TEXT, -- 암호화된 Access Token
    token_expire_at TIMESTAMP WITH TIME ZONE, -- 토큰 만료 시각
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- 5. 트레이딩 규칙 테이블
-- =============================================
CREATE TABLE trade_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID NOT NULL REFERENCES brokerage_accounts(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    symbol VARCHAR(20) NOT NULL, -- 종목코드 (예: AAPL)
    buy_amount_usd NUMERIC(12, 2) NOT NULL, -- 매수 금액 (USD)
    max_position NUMERIC(12, 2) NOT NULL, -- 최대 포지션 금액 (USD)
    entry_condition TEXT NOT NULL, -- 진입 조건 (JSON/YAML)
    exit_condition TEXT NOT NULL, -- 청산 조건 (JSON/YAML)
    time_in_force VARCHAR(10) DEFAULT 'IOC' NOT NULL, -- 주문 유효기간
    cooldown_seconds INTEGER DEFAULT 60 NOT NULL, -- 재진입 쿨다운 (초)
    stop_loss_percent NUMERIC(5, 2), -- 손절 퍼센트
    take_profit_percent NUMERIC(5, 2), -- 익절 퍼센트
    enabled BOOLEAN DEFAULT false NOT NULL,
    last_triggered_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- 6. 주문 테이블
-- =============================================
CREATE TABLE orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID NOT NULL REFERENCES brokerage_accounts(id) ON DELETE CASCADE,
    rule_id UUID REFERENCES trade_rules(id) ON DELETE SET NULL,
    symbol VARCHAR(20) NOT NULL,
    side orderside NOT NULL,
    quantity INTEGER NOT NULL,
    price NUMERIC(12, 4), -- 주문가격 (시장가는 NULL)
    status orderstatus DEFAULT 'PENDING' NOT NULL,
    broker_order_id VARCHAR(100) UNIQUE, -- 브로커 주문번호
    filled_quantity INTEGER DEFAULT 0 NOT NULL,
    avg_fill_price NUMERIC(12, 4),
    commission NUMERIC(8, 4),
    raw_response TEXT, -- 브로커 API 원본 응답 (JSON)
    placed_at TIMESTAMP WITH TIME ZONE,
    filled_at TIMESTAMP WITH TIME ZONE,
    cancelled_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- 7. 포지션 테이블
-- =============================================
CREATE TABLE positions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID NOT NULL REFERENCES brokerage_accounts(id) ON DELETE CASCADE,
    symbol VARCHAR(20) NOT NULL,
    quantity INTEGER NOT NULL,
    avg_price NUMERIC(12, 4) NOT NULL, -- 평균 매수가
    current_price NUMERIC(12, 4), -- 현재가
    unrealized_pnl NUMERIC(12, 2), -- 미실현 손익
    unrealized_pnl_percent NUMERIC(8, 4), -- 미실현 손익률 (%)
    opened_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- 8. 실행 로그 테이블
-- =============================================
CREATE TABLE execution_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID NOT NULL REFERENCES brokerage_accounts(id) ON DELETE CASCADE,
    rule_id UUID REFERENCES trade_rules(id) ON DELETE SET NULL,
    level loglevel DEFAULT 'INFO' NOT NULL,
    category VARCHAR(50) NOT NULL, -- 로그 카테고리 (order, position, auth, etc)
    message TEXT NOT NULL,
    context TEXT, -- 추가 컨텍스트 데이터 (JSON)
    error_code VARCHAR(50),
    error_details TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- 9. 전략 시그널 테이블
-- =============================================
CREATE TABLE strategy_signals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_id UUID NOT NULL REFERENCES trade_rules(id) ON DELETE CASCADE,
    signal_type signaltype NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    score NUMERIC(5, 4), -- 시그널 강도 (0.0 ~ 1.0)
    confidence NUMERIC(5, 4), -- 신뢰도 (0.0 ~ 1.0)
    payload TEXT, -- 시그널 상세 데이터 (JSON)
    executed BOOLEAN DEFAULT false NOT NULL, -- 시그널 실행 여부
    executed_at TIMESTAMP WITH TIME ZONE,
    execution_result TEXT, -- 실행 결과 (JSON)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- 10. 인덱스 생성
-- =============================================
-- 사용자
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);

-- 증권 계좌
CREATE INDEX idx_brokerage_accounts_user_id ON brokerage_accounts(user_id);
CREATE INDEX idx_brokerage_accounts_enabled ON brokerage_accounts(enabled);

-- API 자격증명
CREATE INDEX idx_api_credentials_account_id ON api_credentials(account_id);

-- 트레이딩 규칙
CREATE INDEX idx_trade_rules_account_id ON trade_rules(account_id);
CREATE INDEX idx_trade_rules_symbol ON trade_rules(symbol);
CREATE INDEX idx_trade_rules_enabled ON trade_rules(enabled);

-- 주문
CREATE INDEX idx_orders_account_id ON orders(account_id);
CREATE INDEX idx_orders_rule_id ON orders(rule_id);
CREATE INDEX idx_orders_symbol ON orders(symbol);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_created_at ON orders(created_at);

-- 포지션
CREATE INDEX idx_positions_account_id ON positions(account_id);
CREATE INDEX idx_positions_symbol ON positions(symbol);

-- 실행 로그
CREATE INDEX idx_execution_logs_account_id ON execution_logs(account_id);
CREATE INDEX idx_execution_logs_rule_id ON execution_logs(rule_id);
CREATE INDEX idx_execution_logs_level ON execution_logs(level);
CREATE INDEX idx_execution_logs_category ON execution_logs(category);
CREATE INDEX idx_execution_logs_created_at ON execution_logs(created_at);

-- 전략 시그널
CREATE INDEX idx_strategy_signals_rule_id ON strategy_signals(rule_id);
CREATE INDEX idx_strategy_signals_type ON strategy_signals(signal_type);
CREATE INDEX idx_strategy_signals_symbol ON strategy_signals(symbol);
CREATE INDEX idx_strategy_signals_created_at ON strategy_signals(created_at);

-- 11. 트리거 함수 (updated_at 자동 업데이트)
-- =============================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- updated_at 트리거 생성
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_brokerage_accounts_updated_at BEFORE UPDATE ON brokerage_accounts FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_api_credentials_updated_at BEFORE UPDATE ON api_credentials FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_trade_rules_updated_at BEFORE UPDATE ON trade_rules FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_orders_updated_at BEFORE UPDATE ON orders FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_positions_updated_at BEFORE UPDATE ON positions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 12. 샘플 데이터 (선택적)
-- =============================================
-- 관리자 계정 생성 (비밀번호: admin123)
INSERT INTO users (email, password_hash, name, role, is_active, is_verified) 
VALUES (
    'admin@alpha-ai.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/lewdBWX1GBZEs/3.W',
    'Alpha AI 관리자',
    'ADMIN',
    true,
    true
) ON CONFLICT (email) DO NOTHING;

-- =============================================
-- 스크립트 실행 완료
-- =============================================
SELECT 'Alpha AI Trading System 데이터베이스 초기화 완료!' as result;
