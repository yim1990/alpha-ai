'use client';

import { useKISStatus, getStatusColor } from '@/lib/hooks/useApi';
import { Wifi, WifiOff, RefreshCw, AlertCircle, CheckCircle2 } from 'lucide-react';

export default function KISStatusCard() {
  const { data, isLoading, isError, isFetching } = useKISStatus();

  if (isError) {
    return (
      <div className="card card-body bg-danger-50 border-danger-200">
        <div className="flex items-center gap-3">
          <AlertCircle className="h-6 w-6 text-danger-600" />
          <div>
            <h3 className="font-semibold text-danger-900">KIS API 연결 실패</h3>
            <p className="text-sm text-danger-700">상태를 확인할 수 없습니다</p>
          </div>
        </div>
      </div>
    );
  }

  if (isLoading && !data) {
    return (
      <div className="card card-body">
        <div className="flex items-center gap-3">
          <RefreshCw className="h-6 w-6 animate-spin text-gray-400" />
          <div>
            <h3 className="font-semibold text-gray-900">KIS API 상태</h3>
            <p className="text-sm text-gray-500">상태 확인 중...</p>
          </div>
        </div>
      </div>
    );
  }

  const isConnected = (data as any)?.connected;
  const isTokenValid = (data as any)?.token_valid;

  return (
    <div className={`card card-body ${
      isConnected 
        ? 'bg-success-50 border-success-200' 
        : 'bg-warning-50 border-warning-200'
    }`}>
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          {isConnected ? (
            <CheckCircle2 className="h-6 w-6 text-success-600" />
          ) : (
            <WifiOff className="h-6 w-6 text-warning-600" />
          )}
          <div>
            <h3 className={`font-semibold ${
              isConnected ? 'text-success-900' : 'text-warning-900'
            }`}>
              KIS API {isConnected ? '연결됨' : '연결 안됨'}
            </h3>
            <p className={`text-sm ${
              isConnected ? 'text-success-700' : 'text-warning-700'
            }`}>
              {isConnected ? '실시간 데이터 수신 중' : 'API 연결을 확인해주세요'}
            </p>
          </div>
        </div>
        
        {isFetching && (
          <RefreshCw className="h-4 w-4 animate-spin text-gray-400" />
        )}
      </div>

      {(data as any) && (
        <div className="mt-4 grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="block text-gray-600">토큰 상태</span>
            <span className={`font-medium ${
              isTokenValid ? 'text-success-700' : 'text-danger-700'
            }`}>
              {isTokenValid ? '유효함' : '만료됨'}
            </span>
          </div>
          
          <div>
            <span className="block text-gray-600">일일 API 호출</span>
            <span className="font-medium text-gray-900">
              {(data as any).api_calls_today}회
            </span>
          </div>
          
          {(data as any).last_token_time && (
            <div className="col-span-2">
              <span className="block text-gray-600">마지막 토큰 발급</span>
              <span className="font-medium text-gray-900">
                {new Date((data as any).last_token_time).toLocaleString('ko-KR')}
              </span>
            </div>
          )}
          
          {(data as any).error_message && (
            <div className="col-span-2">
              <span className="block text-gray-600">오류 메시지</span>
              <span className="font-medium text-danger-700">
                {(data as any).error_message}
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
