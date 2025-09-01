'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import { Toaster } from 'sonner';
import { useState } from 'react';
import { AuthProvider } from '@/lib/hooks/useAuth';

export function Providers({ children }: { children: React.ReactNode }) {
  // React Query 클라이언트 생성
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 2 * 1000, // 2초 (실시간 데이터용)
            gcTime: 5 * 60 * 1000, // 5분 (이전 cacheTime)
            retry: 2, // KIS API 재시도
            refetchOnWindowFocus: true, // 포커스 시 데이터 새로고침
            refetchOnReconnect: true, // 재연결 시 데이터 새로고침
          },
          mutations: {
            retry: 1,
          },
        },
      })
  );

  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        {children}
        <Toaster 
          position="top-right"
          richColors
          closeButton
          duration={4000}
        />
      </AuthProvider>
    </QueryClientProvider>
  );
}
