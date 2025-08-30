import Link from 'next/link';
import { ArrowRight, TrendingUp, Shield, Zap, BarChart3 } from 'lucide-react';

export default function HomePage() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-white">
      {/* 헤더 */}
      <header className="border-b bg-white/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4">
          <nav className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <TrendingUp className="h-8 w-8 text-primary-600" />
              <span className="text-xl font-bold">Alpha AI</span>
            </div>
            <div className="flex items-center space-x-4">
              <Link href="/dashboard" className="btn-primary btn-md">
                대시보드 <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </div>
          </nav>
        </div>
      </header>

      {/* 히어로 섹션 */}
      <section className="container mx-auto px-4 py-20">
        <div className="text-center max-w-3xl mx-auto">
          <h1 className="text-5xl font-bold mb-6">
            <span className="text-gradient">AI 기반</span> 미국 주식 자동매매 시스템
          </h1>
          <p className="text-xl text-gray-600 mb-8">
            한국투자증권 Open API를 활용한 스마트한 투자 자동화 솔루션
          </p>
          <div className="flex gap-4 justify-center">
            <Link href="/dashboard" className="btn-primary btn-lg">
              시작하기 <ArrowRight className="ml-2 h-5 w-5" />
            </Link>
            <Link href="#features" className="btn-outline btn-lg">
              더 알아보기
            </Link>
          </div>
        </div>
      </section>

      {/* 주요 기능 */}
      <section id="features" className="container mx-auto px-4 py-20">
        <h2 className="text-3xl font-bold text-center mb-12">주요 기능</h2>
        <div className="grid md:grid-cols-3 gap-8">
          <FeatureCard
            icon={<Zap className="h-10 w-10 text-primary-600" />}
            title="실시간 자동매매"
            description="설정한 규칙에 따라 24시간 자동으로 매수/매도를 수행합니다."
          />
          <FeatureCard
            icon={<Shield className="h-10 w-10 text-primary-600" />}
            title="리스크 관리"
            description="손절/익절, 포지션 한도 등 다양한 리스크 관리 기능을 제공합니다."
          />
          <FeatureCard
            icon={<BarChart3 className="h-10 w-10 text-primary-600" />}
            title="실시간 모니터링"
            description="포지션, 손익, 주문 현황을 실시간으로 모니터링할 수 있습니다."
          />
        </div>
      </section>

      {/* 시스템 상태 */}
      <section className="bg-gray-50 py-20">
        <div className="container mx-auto px-4">
          <h2 className="text-3xl font-bold text-center mb-12">시스템 상태</h2>
          <div className="grid md:grid-cols-4 gap-6">
            <StatusCard label="API 서버" status="정상" />
            <StatusCard label="WebSocket" status="연결됨" />
            <StatusCard label="데이터베이스" status="정상" />
            <StatusCard label="Worker" status="실행중" />
          </div>
        </div>
      </section>

      {/* 푸터 */}
      <footer className="border-t bg-white py-8 mt-20">
        <div className="container mx-auto px-4">
          <div className="flex flex-col md:flex-row justify-between items-center">
            <div className="flex items-center space-x-2 mb-4 md:mb-0">
              <TrendingUp className="h-6 w-6 text-primary-600" />
              <span className="font-semibold">Alpha AI Trading System</span>
            </div>
            <div className="text-sm text-gray-600">
              © 2024 Alpha AI. All rights reserved.
            </div>
          </div>
          <div className="mt-4 text-center text-xs text-gray-500">
            <p className="font-semibold">⚠️ 투자 위험 경고</p>
            <p>
              이 시스템은 교육 및 연구 목적으로 제공됩니다. 실제 투자에 사용할 경우 
              발생하는 모든 손실에 대해 개발자는 책임지지 않습니다.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}

// 기능 카드 컴포넌트
function FeatureCard({ 
  icon, 
  title, 
  description 
}: { 
  icon: React.ReactNode; 
  title: string; 
  description: string;
}) {
  return (
    <div className="card card-body text-center hover:shadow-lg transition-shadow">
      <div className="flex justify-center mb-4">{icon}</div>
      <h3 className="text-xl font-semibold mb-2">{title}</h3>
      <p className="text-gray-600">{description}</p>
    </div>
  );
}

// 상태 카드 컴포넌트
function StatusCard({ label, status }: { label: string; status: string }) {
  const isActive = status === '정상' || status === '연결됨' || status === '실행중';
  
  return (
    <div className="card card-body">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-gray-600">{label}</span>
        <span className={`badge ${isActive ? 'badge-success' : 'badge-danger'}`}>
          {status}
        </span>
      </div>
    </div>
  );
}
