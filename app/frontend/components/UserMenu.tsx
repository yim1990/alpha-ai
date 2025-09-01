'use client';

import { useState } from 'react';
import { User, LogOut, Settings, Shield, ChevronDown } from 'lucide-react';
import { useAuth, getRoleName } from '@/lib/hooks/useAuth';

export default function UserMenu() {
  const { user, logout } = useAuth();
  const [isOpen, setIsOpen] = useState(false);

  if (!user) {
    return null;
  }

  const handleLogout = async () => {
    try {
      await logout();
    } catch (error) {
      console.error('로그아웃 오류:', error);
    }
  };

  const getRoleColor = (role: string) => {
    switch (role) {
      case 'admin': return 'bg-danger-100 text-danger-800';
      case 'trader': return 'bg-primary-100 text-primary-800';
      case 'viewer': return 'bg-gray-100 text-gray-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-100 transition-colors"
      >
        <div className="flex items-center justify-center w-8 h-8 bg-primary-100 rounded-full">
          <User className="h-4 w-4 text-primary-600" />
        </div>
        <div className="hidden md:block text-left">
          <div className="text-sm font-medium text-gray-900">{user.name}</div>
          <div className="text-xs text-gray-500">{user.email}</div>
        </div>
        <ChevronDown className="h-4 w-4 text-gray-400" />
      </button>

      {isOpen && (
        <>
          {/* 오버레이 */}
          <div
            className="fixed inset-0 z-10"
            onClick={() => setIsOpen(false)}
          />
          
          {/* 드롭다운 메뉴 */}
          <div className="absolute right-0 top-full mt-2 w-64 bg-white rounded-lg shadow-lg border border-gray-200 z-20">
            {/* 사용자 정보 */}
            <div className="p-4 border-b border-gray-200">
              <div className="flex items-center gap-3">
                <div className="flex items-center justify-center w-10 h-10 bg-primary-100 rounded-full">
                  <User className="h-5 w-5 text-primary-600" />
                </div>
                <div className="flex-1">
                  <div className="font-medium text-gray-900">{user.name}</div>
                  <div className="text-sm text-gray-500">{user.email}</div>
                  <div className="mt-1">
                    <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${getRoleColor(user.role)}`}>
                      <Shield className="h-3 w-3" />
                      {getRoleName(user.role)}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* 메뉴 항목들 */}
            <div className="p-2">
              <button
                onClick={() => {
                  setIsOpen(false);
                  // TODO: 설정 페이지로 이동
                }}
                className="w-full flex items-center gap-3 px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <Settings className="h-4 w-4" />
                계정 설정
              </button>
              
              <button
                onClick={() => {
                  setIsOpen(false);
                  handleLogout();
                }}
                className="w-full flex items-center gap-3 px-3 py-2 text-sm text-danger-700 hover:bg-danger-50 rounded-lg transition-colors"
              >
                <LogOut className="h-4 w-4" />
                로그아웃
              </button>
            </div>

            {/* 상태 정보 */}
            <div className="p-4 border-t border-gray-200 bg-gray-50 rounded-b-lg">
              <div className="flex items-center justify-between text-xs text-gray-500">
                <span>상태: {user.is_active ? '활성' : '비활성'}</span>
                <span>인증: {user.is_verified ? '완료' : '대기'}</span>
              </div>
              {user.last_login_at && (
                <div className="mt-1 text-xs text-gray-400">
                  마지막 로그인: {new Date(user.last_login_at).toLocaleString('ko-KR')}
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
