import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { Providers } from './providers';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'Alpha AI Trading System',
  description: 'KIS Open API 기반 미국 주식 자동매매 시스템',
  keywords: '주식, 자동매매, 트레이딩, KIS, 한국투자증권',
  authors: [{ name: 'Jason Im' }],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko">
      <body className={inter.className}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
