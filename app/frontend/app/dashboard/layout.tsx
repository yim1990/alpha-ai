'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { 
  TrendingUp, 
  Home, 
  Wallet, 
  FileText, 
  ShoppingCart, 
  BarChart3,
  Settings,
  LogOut,
  Menu,
  X
} from 'lucide-react';
import { useState } from 'react';
import { signOut } from 'next-auth/react';

const navigation = [
  { name: '대시보드', href: '/dashboard', icon: Home },
  { name: '계좌 관리', href: '/dashboard/accounts', icon: Wallet },
  { name: '매매 규칙', href: '/dashboard/rules', icon: FileText },
  { name: '주문 내역', href: '/dashboard/orders', icon: ShoppingCart },
  { name: '포지션', href: '/dashboard/positions', icon: BarChart3 },
  { name: '설정', href: '/dashboard/settings', icon: Settings },
];

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 모바일 사이드바 토글 */}
      <div className="lg:hidden fixed top-4 left-4 z-50">
        <button
          onClick={() => setSidebarOpen(!sidebarOpen)}
          className="p-2 rounded-md bg-white shadow-md"
        >
          {sidebarOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
        </button>
      </div>

      {/* 사이드바 */}
      <aside
        className={`
          fixed inset-y-0 left-0 z-40 w-64 bg-white border-r border-gray-200
          transform transition-transform duration-200 ease-in-out
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
          lg:translate-x-0 lg:static lg:inset-0
        `}
      >
        <div className="flex flex-col h-full">
          {/* 로고 */}
          <div className="flex items-center h-16 px-6 border-b border-gray-200">
            <TrendingUp className="h-8 w-8 text-primary-600 mr-3" />
            <span className="text-xl font-bold">Alpha AI</span>
          </div>

          {/* 네비게이션 */}
          <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
            {navigation.map((item) => {
              const isActive = pathname === item.href;
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  className={`
                    flex items-center px-3 py-2 text-sm font-medium rounded-md
                    transition-colors duration-150 ease-in-out
                    ${
                      isActive
                        ? 'bg-primary-50 text-primary-700'
                        : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
                    }
                  `}
                  onClick={() => setSidebarOpen(false)}
                >
                  <item.icon className="mr-3 h-5 w-5 flex-shrink-0" />
                  {item.name}
                </Link>
              );
            })}
          </nav>

          {/* 사용자 정보 */}
          <div className="border-t border-gray-200 p-4">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="h-10 w-10 rounded-full bg-primary-100 flex items-center justify-center">
                  <span className="text-primary-700 font-semibold">JI</span>
                </div>
              </div>
              <div className="ml-3 flex-1">
                <p className="text-sm font-medium text-gray-700">Jason Im</p>
                <p className="text-xs text-gray-500">관리자</p>
              </div>
              <button
                onClick={() => signOut()}
                className="ml-auto p-2 text-gray-400 hover:text-gray-600"
              >
                <LogOut className="h-5 w-5" />
              </button>
            </div>
          </div>
        </div>
      </aside>

      {/* 메인 컨텐츠 */}
      <main className="lg:ml-64">
        <div className="px-4 sm:px-6 lg:px-8 py-8">
          {children}
        </div>
      </main>

      {/* 모바일 사이드바 오버레이 */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-gray-600 bg-opacity-50 z-30 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}
    </div>
  );
}
