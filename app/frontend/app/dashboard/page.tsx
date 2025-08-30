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
  ArrowDownRight
} from 'lucide-react';

export default function DashboardPage() {
  // 임시 데이터 (실제로는 API에서 가져옴)
  const stats = {
    totalBalance: 125000.50,
    dailyPnL: 2340.20,
    dailyPnLPercent: 1.92,
    openPositions: 8,
    pendingOrders: 3,
    accountHealth: 'healthy'
  };

  const recentOrders = [
    { id: '1', symbol: 'AAPL', side: 'BUY', qty: 10, price: 175.50, status: 'filled', time: '10:30' },
    { id: '2', symbol: 'MSFT', side: 'SELL', qty: 5, price: 380.20, status: 'filled', time: '10:15' },
    { id: '3', symbol: 'GOOGL', side: 'BUY', qty: 3, price: 140.80, status: 'pending', time: '10:00' },
  ];

  const positions = [
    { symbol: 'AAPL', qty: 50, avgPrice: 170.20, currentPrice: 175.50, pnl: 265.00, pnlPercent: 3.11 },
    { symbol: 'TSLA', qty: 20, avgPrice: 245.50, currentPrice: 238.90, pnl: -132.00, pnlPercent: -2.69 },
    { symbol: 'NVDA', qty: 15, avgPrice: 450.00, currentPrice: 468.50, pnl: 277.50, pnlPercent: 4.11 },
  ];

  return (
    <div className="space-y-6">
      {/* 페이지 헤더 */}
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900">대시보드</h1>
        <div className="flex items-center space-x-2">
          <span className="text-sm text-gray-500">마지막 업데이트:</span>
          <span className="text-sm font-medium">2024-03-15 14:30:25</span>
        </div>
      </div>

      {/* 통계 카드 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="총 자산"
          value={`$${stats.totalBalance.toLocaleString()}`}
          icon={<DollarSign className="h-5 w-5" />}
          trend="neutral"
        />
        <StatCard
          title="일일 손익"
          value={`$${stats.dailyPnL.toLocaleString()}`}
          subValue={`${stats.dailyPnLPercent > 0 ? '+' : ''}${stats.dailyPnLPercent}%`}
          icon={stats.dailyPnL >= 0 ? <TrendingUp className="h-5 w-5" /> : <TrendingDown className="h-5 w-5" />}
          trend={stats.dailyPnL >= 0 ? 'up' : 'down'}
        />
        <StatCard
          title="오픈 포지션"
          value={stats.openPositions.toString()}
          icon={<Activity className="h-5 w-5" />}
          trend="neutral"
        />
        <StatCard
          title="계좌 상태"
          value={stats.accountHealth === 'healthy' ? '정상' : '점검필요'}
          icon={stats.accountHealth === 'healthy' ? 
            <CheckCircle className="h-5 w-5" /> : 
            <AlertCircle className="h-5 w-5" />
          }
          trend={stats.accountHealth === 'healthy' ? 'up' : 'down'}
        />
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
                {recentOrders.map((order) => (
                  <tr key={order.id}>
                    <td className="font-medium">{order.symbol}</td>
                    <td>
                      <span className={`badge ${order.side === 'BUY' ? 'badge-success' : 'badge-danger'}`}>
                        {order.side}
                      </span>
                    </td>
                    <td>{order.qty}</td>
                    <td>${order.price}</td>
                    <td>
                      <span className={`badge ${
                        order.status === 'filled' ? 'badge-success' : 
                        order.status === 'pending' ? 'badge-warning' : 
                        'badge-info'
                      }`}>
                        {order.status}
                      </span>
                    </td>
                  </tr>
                ))}
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
                {positions.map((position) => (
                  <tr key={position.symbol}>
                    <td className="font-medium">{position.symbol}</td>
                    <td>{position.qty}</td>
                    <td>${position.avgPrice}</td>
                    <td>${position.currentPrice}</td>
                    <td>
                      <div className={`flex items-center ${position.pnl >= 0 ? 'text-success-600' : 'text-danger-600'}`}>
                        {position.pnl >= 0 ? 
                          <ArrowUpRight className="h-4 w-4 mr-1" /> : 
                          <ArrowDownRight className="h-4 w-4 mr-1" />
                        }
                        <span className="font-medium">
                          ${Math.abs(position.pnl).toFixed(2)}
                        </span>
                        <span className="ml-1 text-sm">
                          ({position.pnlPercent > 0 ? '+' : ''}{position.pnlPercent}%)
                        </span>
                      </div>
                    </td>
                  </tr>
                ))}
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
  trend 
}: { 
  title: string;
  value: string;
  subValue?: string;
  icon: React.ReactNode;
  trend: 'up' | 'down' | 'neutral';
}) {
  const trendColors = {
    up: 'text-success-600 bg-success-50',
    down: 'text-danger-600 bg-danger-50',
    neutral: 'text-gray-600 bg-gray-50'
  };

  return (
    <div className="card card-body">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-gray-600">{title}</span>
        <div className={`p-2 rounded-lg ${trendColors[trend]}`}>
          {icon}
        </div>
      </div>
      <div className="flex items-baseline">
        <span className="text-2xl font-bold text-gray-900">{value}</span>
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
