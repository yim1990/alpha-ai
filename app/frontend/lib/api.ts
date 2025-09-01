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
  sandbox_mode: boolean;
  token_valid: boolean;
  last_check: string;
  rate_limit: {
    remaining: number;
    total: number;
    reset_at: string;
  };
}

export interface MarketData {
  symbol: string;
  name: string;
  price: number;
  change: number;
  change_percent: number;
  volume: number;
  market_cap: string;
  timestamp: string;
  source: string;
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
  total_accounts: number;
  active_accounts: number;
  total_rules: number;
  active_rules: number;
  total_positions: number;
  total_value_usd: number;
  daily_pnl: number;
  daily_pnl_percent: number;
  last_updated: string;
}

export interface SystemStatus {
  api_server: string;
  kis_api: string;
  websocket: string;
  trading_bot: string;
  data_sync: string;
  last_update: string;
}

// 인증 관련 인터페이스
export interface User {
  id: string;
  email: string;
  name: string;
  role: 'admin' | 'trader' | 'viewer';
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
  last_login_at: string | null;
}

export interface UserCreate {
  email: string;
  password: string;
  name: string;
  role?: 'admin' | 'trader' | 'viewer';
}

export interface UserLogin {
  email: string;
  password: string;
}

export interface LoginResponse {
  user: User;
  token: {
    access_token: string;
    token_type: string;
    expires_in: number;
  };
}

export interface PasswordChange {
  current_password: string;
  new_password: string;
}

export interface PasswordStrengthResult {
  valid: boolean;
  score: number;
  errors: string[];
}

export interface ApiResponse {
  success: boolean;
  message: string;
  data?: any;
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

  // 인증 관련 API
  auth: {
    // 회원가입
    async register(userData: UserCreate): Promise<User> {
      const response = await apiClient.post<User>('/api/auth/register', userData);
      return response.data;
    },

    // 로그인
    async login(loginData: UserLogin): Promise<LoginResponse> {
      const response = await apiClient.post<LoginResponse>('/api/auth/login', loginData);
      
      // 로그인 성공 시 토큰을 axios 헤더에 설정
      if (response.data.token.access_token) {
        apiClient.defaults.headers.common['Authorization'] = 
          `Bearer ${response.data.token.access_token}`;
        
        // 로컬 스토리지에 토큰 저장
        localStorage.setItem('access_token', response.data.token.access_token);
        localStorage.setItem('user', JSON.stringify(response.data.user));
      }
      
      return response.data;
    },

    // 로그아웃
    async logout(): Promise<ApiResponse> {
      try {
        const response = await apiClient.post<ApiResponse>('/api/auth/logout');
        
        // 토큰 및 사용자 정보 삭제
        delete apiClient.defaults.headers.common['Authorization'];
        localStorage.removeItem('access_token');
        localStorage.removeItem('user');
        
        return response.data;
      } catch (error) {
        // 오류가 발생해도 로컬 데이터는 정리
        delete apiClient.defaults.headers.common['Authorization'];
        localStorage.removeItem('access_token');
        localStorage.removeItem('user');
        throw error;
      }
    },

    // 현재 사용자 정보
    async getCurrentUser(): Promise<User> {
      const response = await apiClient.get<User>('/api/auth/me');
      return response.data;
    },

    // 비밀번호 변경
    async changePassword(passwordData: PasswordChange): Promise<ApiResponse> {
      const response = await apiClient.post<ApiResponse>('/api/auth/change-password', passwordData);
      return response.data;
    },

    // 비밀번호 강도 확인
    async checkPasswordStrength(password: string): Promise<PasswordStrengthResult> {
      const response = await apiClient.post<PasswordStrengthResult>(
        '/api/auth/check-password-strength', 
        { password }
      );
      return response.data;
    },

    // 토큰 검증
    async verifyToken(): Promise<User> {
      const response = await apiClient.get<User>('/api/auth/verify-token');
      return response.data;
    },

    // 토큰 초기화 (페이지 로드 시)
    initializeAuth(): void {
      const token = localStorage.getItem('access_token');
      if (token) {
        apiClient.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      }
    },

    // 인증 상태 확인
    isAuthenticated(): boolean {
      return !!localStorage.getItem('access_token');
    },

    // 저장된 사용자 정보 가져오기
    getStoredUser(): User | null {
      const userStr = localStorage.getItem('user');
      return userStr ? JSON.parse(userStr) : null;
    },
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
