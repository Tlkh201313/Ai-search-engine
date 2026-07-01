import type { Metadata, Viewport } from 'next';

import { Providers } from '@/components/Providers';

import './globals.css';

export const metadata: Metadata = {
  title: 'Lumen — the grounded answer engine',
  description:
    'Ask anything and get a fast, source-backed answer with real citations. Lumen searches the web, reads the pages, ranks the evidence, and shows its work.',
  applicationName: 'Lumen',
  keywords: ['AI search', 'research engine', 'citations', 'answer engine'],
};

export const viewport: Viewport = {
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: '#f9f8f4' },
    { media: '(prefers-color-scheme: dark)', color: '#151411' },
  ],
  width: 'device-width',
  initialScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-dvh antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
