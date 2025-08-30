'use client';

import { 
  TrendingUp, 
  TrendingDown, 
  DollarSign, 
  Activity, 
  AlertCircle,
  CheckCircle,
  Clock,
  ArrowUpRight,
  ArrowDownRight,
  RefreshCw
} from 'lucide-react';

import RealTimeStockCard from '@/components/RealTimeStockCard';
import KISStatusCard from '@/components/KISStatusCard';
import { 
  useDashboardStats, 
  useOverallStatus, 
  useMainStocks,
  formatPrice,
  formatPercent,
  getChangeColor 
} from '@/lib/hooks/useApi';

export default function DashboardPage() {
  // 실시간 데이터 훅 사용
  const { data: dashboardStats, isLoading: statsLoading, isFetching: statsFetching } = useDashboardStats();
  const { isLoading: overallLoading, hasData } = useOverallStatus();
  const mainStocksQueries = useMainStocks();

  // 로딩 상태
  if (overallLoading && !hasData) {
    return (
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <h1 className="text-2xl font-bold text-gray-900">대시보드</h1>
          <RefreshCw className="h-5 w-5 animate-spin text-gray-400" />
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="card card-body animate-pulse">
              <div className="h-4 bg-gray-200 rounded mb-2"></div>
              <div className="h-8 bg-gray-200 rounded mb-2"></div>
              <div className="h-3 bg-gray-200 rounded w-1/2"></div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 페이지 헤더 */}
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900">실시간 대시보드</h1>
        <div className="flex items-center space-x-3">
          {statsFetching && <RefreshCw className="h-4 w-4 animate-spin text-primary-500" />}
          <div className="text-right">
            <div className="text-sm text-gray-500">데이터 소스</div>
            <div className="text-sm font-medium text-primary-600">
              {(dashboardStats as any)?.data_source || 'KIS API'}
            </div>
          </div>
          <div className="text-right">
            <div className="text-sm text-gray-500">마지막 업데이트</div>
            <div className="text-sm font-medium">
              {new Date().toLocaleTimeString('ko-KR')}
            </div>
          </div>
        </div>
      </div>

      {/* KIS API 상태 */}
      <KISStatusCard />

      {/* 통계 카드 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="총 자산"
          value={formatPrice((dashboardStats as any)?.total_balance)}
          icon={<DollarSign className="h-5 w-5" />}
          trend="neutral"
          isLoading={statsLoading}
        />
        <StatCard
          title="일일 손익"
          value={formatPrice((dashboardStats as any)?.daily_pnl)}
          subValue={formatPercent((dashboardStats as any)?.daily_pnl_percent)}
          icon={(dashboardStats as any) && (dashboardStats as any).daily_pnl >= 0 ? 
            <TrendingUp className="h-5 w-5" /> : 
            <TrendingDown className="h-5 w-5" />
          }
          trend={(dashboardStats as any) && (dashboardStats as any).daily_pnl >= 0 ? 'up' : 'down'}
          isLoading={statsLoading}
        />
        <StatCard
          title="오픈 포지션"
          value={(dashboardStats as any)?.open_positions?.toString() || '0'}
          icon={<Activity className="h-5 w-5" />}
          trend="neutral"
          isLoading={statsLoading}
        />
        <StatCard
          title="KIS 연결"
          value={(dashboardStats as any)?.kis_connected ? 'KIS 연결됨' : 'KIS 연결 안됨'}
          icon={(dashboardStats as any)?.kis_connected ? 
            <CheckCircle className="h-5 w-5" /> : 
            <AlertCircle className="h-5 w-5" />
          }
          trend={(dashboardStats as any)?.kis_connected ? 'up' : 'down'}
          isLoading={statsLoading}
        />
      </div>

      {/* 실시간 주식 시세 */}
      <div>
        <h2 className="text-lg font-semibold mb-4">실시간 주식 시세</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
          <RealTimeStockCard symbol="AAPL" />
          <RealTimeStockCard symbol="TSLA" />
          <RealTimeStockCard symbol="NVDA" />
          <RealTimeStockCard symbol="MSFT" />
          <RealTimeStockCard symbol="GOOGL" />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 최근 주문 */}
        <div className="card">
          <div className="card-header flex justify-between items-center">
            <h2 className="text-lg font-semibold">최근 주문</h2>
            <button className="text-sm text-primary-600 hover:text-primary-700">
              전체보기 →
            </button>
          </div>
          <div className="card-body p-0">
            <table className="table">
              <thead>
                <tr>
                  <th>종목</th>
                  <th>구분</th>
                  <th>수량</th>
                  <th>가격</th>
                  <th>상태</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td colSpan={5} className="text-center py-8 text-gray-500">
                    <Activity className="h-8 w-8 mx-auto mb-2 text-gray-400" />
                    <p>주문 데이터를 불러오는 중입니다...</p>
                    <p className="text-sm">실제 주문 기능 구현 시 데이터가 표시됩니다.</p>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        {/* 현재 포지션 */}
        <div className="card">
          <div className="card-header flex justify-between items-center">
            <h2 className="text-lg font-semibold">현재 포지션</h2>
            <button className="text-sm text-primary-600 hover:text-primary-700">
              전체보기 →
            </button>
          </div>
          <div className="card-body p-0">
            <table className="table">
              <thead>
                <tr>
                  <th>종목</th>
                  <th>수량</th>
                  <th>평단가</th>
                  <th>현재가</th>
                  <th>손익</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td colSpan={5} className="text-center py-8 text-gray-500">
                    <TrendingUp className="h-8 w-8 mx-auto mb-2 text-gray-400" />
                    <p>포지션 데이터를 불러오는 중입니다...</p>
                    <p className="text-sm">실제 계좌 연동 시 데이터가 표시됩니다.</p>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* 시스템 상태 */}
      <div className="card">
        <div className="card-header">
          <h2 className="text-lg font-semibold">시스템 상태</h2>
        </div>
        <div className="card-body">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <SystemStatus label="API 연결" status="connected" />
            <SystemStatus label="WebSocket" status="connected" />
            <SystemStatus label="자동매매 봇" status="running" />
            <SystemStatus label="데이터 동기화" status="synced" />
          </div>
        </div>
      </div>
    </div>
  );
}

// 통계 카드 컴포넌트
function StatCard({ 
  title, 
  value, 
  subValue,
  icon, 
  trend,
  isLoading = false
}: { 
  title: string;
  value: string | null | undefined;
  subValue?: string;
  icon: React.ReactNode;
  trend: 'up' | 'down' | 'neutral';
  isLoading?: boolean;
}) {
  const trendColors = {
    up: 'text-success-600 bg-success-50',
    down: 'text-danger-600 bg-danger-50',
    neutral: 'text-gray-600 bg-gray-50'
  };

  if (isLoading) {
    return (
      <div className="card card-body animate-pulse">
        <div className="flex items-center justify-between mb-2">
          <div className="h-4 bg-gray-200 rounded w-20"></div>
          <div className="h-8 w-8 bg-gray-200 rounded-lg"></div>
        </div>
        <div className="flex items-baseline">
          <div className="h-8 bg-gray-200 rounded w-24"></div>
          <div className="h-4 bg-gray-200 rounded w-12 ml-2"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="card card-body hover:shadow-md transition-shadow">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-gray-600">{title}</span>
        <div className={`p-2 rounded-lg ${trendColors[trend]}`}>
          {icon}
        </div>
      </div>
      <div className="flex items-baseline">
        <span className="text-2xl font-bold text-gray-900">
          {value || 'N/A'}
        </span>
        {subValue && (
          <span className={`ml-2 text-sm font-medium ${
            trend === 'up' ? 'text-success-600' : 
            trend === 'down' ? 'text-danger-600' : 
            'text-gray-600'
          }`}>
            {subValue}
          </span>
        )}
      </div>
    </div>
  );
}

// 시스템 상태 컴포넌트
function SystemStatus({ label, status }: { label: string; status: string }) {
  const statusConfig = {
    connected: { text: '연결됨', color: 'bg-success-500' },
    disconnected: { text: '연결 끊김', color: 'bg-danger-500' },
    running: { text: '실행중', color: 'bg-success-500' },
    stopped: { text: '중지됨', color: 'bg-gray-500' },
    synced: { text: '동기화됨', color: 'bg-success-500' },
    syncing: { text: '동기화중', color: 'bg-warning-500' }
  };

  const config = statusConfig[status as keyof typeof statusConfig] || 
    { text: status, color: 'bg-gray-500' };

  return (
    <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
      <span className="text-sm font-medium text-gray-700">{label}</span>
      <div className="flex items-center">
        <div className={`h-2 w-2 rounded-full ${config.color} mr-2 animate-pulse`} />
        <span className="text-sm text-gray-600">{config.text}</span>
      </div>
    </div>
  );
}
