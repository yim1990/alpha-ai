/**
 * API 관련 React Query 훅들
 * 실시간 데이터 페칭과 캐싱을 관리합니다.
 */

import { useQuery, useQueries, UseQueryResult } from '@tanstack/react-query';
import { 
  api, 
  HealthStatus, 
  KISStatus, 
  MarketData, 
  AccountInfo, 
  DashboardStats, 
  SystemStatus,
  handleApiError
} from '../api';

// Query Keys (캐시 관리용)
export const queryKeys = {
  health: ['health'],
  kisStatus: ['kis-status'],
  marketData: (symbol: string) => ['market-data', symbol],
  accounts: ['accounts'],
  dashboardStats: ['dashboard-stats'],
  systemStatus: ['system-status'],
} as const;

/**
 * 헬스체크 훅
 */
export const useHealth = (enabled = true) => {
  return useQuery({
    queryKey: queryKeys.health,
    queryFn: api.getHealth,
    refetchInterval: 30000, // 30초마다 새로고침
    enabled,
    retry: 3,
  });
};

/**
 * KIS API 상태 훅
 */
export const useKISStatus = (enabled = true) => {
  return useQuery({
    queryKey: queryKeys.kisStatus,
    queryFn: api.getKISStatus,
    refetchInterval: 10000, // 10초마다 새로고침
    enabled,
    retry: 2,
  });
};

/**
 * 단일 종목 시세 훅
 */
export const useMarketData = (symbol: string, enabled = true) => {
  return useQuery({
    queryKey: queryKeys.marketData(symbol),
    queryFn: () => api.getMarketData(symbol),
    refetchInterval: 5000, // 5초마다 새로고침 (실시간 시세)
    enabled: enabled && !!symbol,
    retry: 2,
    staleTime: 2000, // 2초간 최신 데이터로 간주
  });
};

/**
 * 여러 종목 시세 훅
 */
export const useMultipleMarketData = (symbols: string[], enabled = true) => {
  return useQueries({
    queries: symbols.map(symbol => ({
      queryKey: queryKeys.marketData(symbol),
      queryFn: () => api.getMarketData(symbol),
      refetchInterval: 5000,
      enabled: enabled && !!symbol,
      retry: 2,
      staleTime: 2000,
    })),
  });
};

/**
 * 계좌 목록 훅
 */
export const useAccounts = (enabled = true) => {
  return useQuery({
    queryKey: queryKeys.accounts,
    queryFn: api.getAccounts,
    refetchInterval: 30000, // 30초마다 새로고침
    enabled,
    retry: 2,
  });
};

/**
 * 대시보드 통계 훅
 */
export const useDashboardStats = (enabled = true) => {
  return useQuery<DashboardStats>({
    queryKey: queryKeys.dashboardStats,
    queryFn: api.getDashboardStats,
    refetchInterval: 10000, // 10초마다 새로고침
    enabled,
    retry: 2,
  });
};

/**
 * 시스템 상태 훅
 */
export const useSystemStatus = (enabled = true) => {
  return useQuery({
    queryKey: queryKeys.systemStatus,
    queryFn: api.getSystemStatus,
    refetchInterval: 15000, // 15초마다 새로고침
    enabled,
    retry: 2,
  });
};

/**
 * 주요 종목들의 실시간 시세 (대시보드용)
 */
export const useMainStocks = (enabled = true) => {
  const symbols = ['AAPL', 'TSLA', 'NVDA', 'MSFT', 'GOOGL'];
  
  return useMultipleMarketData(symbols, enabled);
};

/**
 * 전체 시스템 상태 조합 훅 (대시보드 메인에서 사용)
 */
export const useOverallStatus = (enabled = true) => {
  const health = useHealth(enabled);
  const kisStatus = useKISStatus(enabled);
  const systemStatus = useSystemStatus(enabled);
  const dashboardStats = useDashboardStats(enabled);
  
  return {
    health,
    kisStatus,
    systemStatus,
    dashboardStats,
    isLoading: health.isLoading || kisStatus.isLoading || systemStatus.isLoading || dashboardStats.isLoading,
    isError: health.isError || kisStatus.isError || systemStatus.isError || dashboardStats.isError,
    hasData: health.data && kisStatus.data && systemStatus.data && dashboardStats.data,
  };
};

// 유틸리티 함수들
export const formatPrice = (price: number | null): string => {
  if (price === null || price === undefined) return 'N/A';
  return `$${price.toFixed(2)}`;
};

export const formatPercent = (percent: number | null): string => {
  if (percent === null || percent === undefined) return 'N/A';
  const sign = percent >= 0 ? '+' : '';
  return `${sign}${percent.toFixed(2)}%`;
};

export const formatVolume = (volume: number | null): string => {
  if (volume === null || volume === undefined) return 'N/A';
  if (volume >= 1_000_000) {
    return `${(volume / 1_000_000).toFixed(1)}M`;
  } else if (volume >= 1_000) {
    return `${(volume / 1_000).toFixed(1)}K`;
  }
  return volume.toLocaleString();
};

export const getChangeColor = (change: number | null): string => {
  if (change === null || change === undefined) return 'text-gray-500';
  return change >= 0 ? 'text-success-600' : 'text-danger-600';
};

export const getStatusColor = (status: string): string => {
  switch (status.toLowerCase()) {
    case 'healthy':
    case 'connected':
    case 'running':
    case 'synced':
      return 'text-success-600';
    case 'warning':
    case 'disconnected':
    case 'inactive':
      return 'text-warning-600';
    case 'error':
    case 'failed':
      return 'text-danger-600';
    default:
      return 'text-gray-500';
  }
};
