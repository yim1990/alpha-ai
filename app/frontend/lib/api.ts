/**
 * API 클라이언트
 * 백엔드 서버와 통신하기 위한 함수들을 정의합니다.
 */

import axios from 'axios';

// API 베이스 URL (환경에 따라 자동 설정)
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Axios 인스턴스 생성
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 요청 인터셉터 (로깅)
apiClient.interceptors.request.use(
  (config) => {
    console.log(`🔄 API Request: ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    console.error('❌ Request Error:', error);
    return Promise.reject(error);
  }
);

// 응답 인터셉터 (에러 처리)
apiClient.interceptors.response.use(
  (response) => {
    console.log(`✅ API Response: ${response.status} ${response.config.url}`);
    return response;
  },
  (error) => {
    console.error('❌ Response Error:', error.response?.status, error.response?.data);
    return Promise.reject(error);
  }
);

// TypeScript 타입 정의
export interface HealthStatus {
  status: string;
  app: string;
  version: string;
  environment: string;
  kis_connected: boolean;
  timestamp: string;
}

export interface KISStatus {
  connected: boolean;
  last_token_time: string | null;
  token_valid: boolean;
  api_calls_today: number;
  error_message: string | null;
}

export interface MarketData {
  symbol: string;
  current_price: number | null;
  previous_close: number | null;
  change_percent: number | null;
  volume: number | null;
  last_updated: string | null;
}

export interface AccountInfo {
  id: string;
  nickname: string;
  broker: string;
  market: string;
  enabled: boolean;
  health_status: string;
  last_heartbeat: string | null;
  kis_connected: boolean;
}

export interface DashboardStats {
  total_balance: number;
  daily_pnl: number;
  daily_pnl_percent: number;
  open_positions: number;
  pending_orders: number;
  account_health: string;
  kis_connected: boolean;
  data_source: string;
  last_updated?: string;
}

export interface SystemStatus {
  api_server: string;
  kis_api: string;
  websocket: string;
  trading_bot: string;
  data_sync: string;
  last_update: string;
}

// API 함수들
export const api = {
  // 헬스체크
  async getHealth(): Promise<HealthStatus> {
    const response = await apiClient.get<HealthStatus>('/health');
    return response.data;
  },

  // KIS API 상태
  async getKISStatus(): Promise<KISStatus> {
    const response = await apiClient.get<KISStatus>('/api/kis/status');
    return response.data;
  },

  // 실시간 시세 조회
  async getMarketData(symbol: string): Promise<MarketData> {
    const response = await apiClient.get<MarketData>(`/api/market/${symbol}`);
    return response.data;
  },

  // 여러 종목 시세 조회
  async getMultipleMarketData(symbols: string[]): Promise<MarketData[]> {
    const promises = symbols.map(symbol => this.getMarketData(symbol));
    return Promise.all(promises);
  },

  // 계좌 목록
  async getAccounts(): Promise<AccountInfo[]> {
    const response = await apiClient.get<AccountInfo[]>('/api/accounts');
    return response.data;
  },

  // 대시보드 통계
  async getDashboardStats(): Promise<DashboardStats> {
    const response = await apiClient.get<DashboardStats>('/api/dashboard/stats');
    return response.data;
  },

  // 시스템 상태
  async getSystemStatus(): Promise<SystemStatus> {
    const response = await apiClient.get<SystemStatus>('/api/system/status');
    return response.data;
  },
};

// 에러 처리 유틸리티
export class ApiError extends Error {
  constructor(
    message: string,
    public status?: number,
    public data?: any
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

// API 에러 핸들러
export const handleApiError = (error: any): ApiError => {
  if (error.response) {
    // 서버 응답이 있는 경우
    return new ApiError(
      error.response.data?.message || 'API 서버 오류',
      error.response.status,
      error.response.data
    );
  } else if (error.request) {
    // 요청이 전송되었지만 응답이 없는 경우
    return new ApiError('서버와 연결할 수 없습니다. 백엔드 서버를 확인해주세요.');
  } else {
    // 요청 설정 중 오류
    return new ApiError(error.message || '알 수 없는 오류가 발생했습니다.');
  }
};

export default api;
