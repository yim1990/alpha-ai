'use client';

import { useMarketData, formatPrice, formatPercent, getChangeColor } from '@/lib/hooks/useApi';
import { ArrowUpRight, ArrowDownRight, Loader2, Wifi, WifiOff } from 'lucide-react';

interface RealTimeStockCardProps {
  symbol: string;
  className?: string;
}

export default function RealTimeStockCard({ symbol, className = '' }: RealTimeStockCardProps) {
  const { data, isLoading, isError, isFetching } = useMarketData(symbol);

  if (isError) {
    return (
      <div className={`card card-body ${className}`}>
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-lg font-semibold text-gray-900">{symbol}</h3>
          <WifiOff className="h-5 w-5 text-danger-500" />
        </div>
        <p className="text-sm text-danger-600">데이터를 불러올 수 없습니다</p>
      </div>
    );
  }

  if (isLoading && !data) {
    return (
      <div className={`card card-body ${className}`}>
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-lg font-semibold text-gray-900">{symbol}</h3>
          <Loader2 className="h-5 w-5 animate-spin text-gray-400" />
        </div>
        <div className="space-y-2">
          <div className="h-4 bg-gray-200 rounded animate-pulse"></div>
          <div className="h-3 bg-gray-200 rounded w-2/3 animate-pulse"></div>
        </div>
      </div>
    );
  }

  const change = (data as any)?.change_percent;
  const changeColor = getChangeColor(change);
  const isPositive = change !== null && change >= 0;

  return (
    <div className={`card card-body hover:shadow-md transition-shadow ${className}`}>
      {/* 헤더 */}
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-lg font-semibold text-gray-900">{symbol}</h3>
        <div className="flex items-center gap-2">
          {isFetching && <Loader2 className="h-4 w-4 animate-spin text-primary-500" />}
          <Wifi className="h-4 w-4 text-success-500" />
        </div>
      </div>

      {/* 현재가 */}
      <div className="mb-2">
        <span className="text-2xl font-bold text-gray-900">
          {formatPrice((data as any)?.current_price)}
        </span>
      </div>

      {/* 변동률 및 변동액 */}
      <div className="flex items-center gap-2 mb-3">
        {isPositive ? (
          <ArrowUpRight className={`h-4 w-4 ${changeColor}`} />
        ) : (
          <ArrowDownRight className={`h-4 w-4 ${changeColor}`} />
        )}
        <span className={`text-sm font-medium ${changeColor}`}>
          {formatPercent(change)}
        </span>
        {(data as any)?.previous_close && (data as any)?.current_price && (
          <span className={`text-sm ${changeColor}`}>
            ({isPositive ? '+' : ''}
            {formatPrice((data as any).current_price - (data as any).previous_close)})
          </span>
        )}
      </div>

      {/* 추가 정보 */}
      <div className="grid grid-cols-2 gap-3 text-sm">
        <div>
          <span className="text-gray-500">전일종가</span>
          <div className="font-medium">{formatPrice((data as any)?.previous_close)}</div>
        </div>
        <div>
          <span className="text-gray-500">거래량</span>
          <div className="font-medium">
            {(data as any)?.volume ? (data as any).volume.toLocaleString() : 'N/A'}
          </div>
        </div>
      </div>

      {/* 마지막 업데이트 시간 */}
      {(data as any)?.last_updated && (
        <div className="mt-3 pt-3 border-t border-gray-100">
          <span className="text-xs text-gray-400">
            업데이트: {new Date((data as any).last_updated).toLocaleTimeString('ko-KR')}
          </span>
        </div>
      )}
    </div>
  );
}
