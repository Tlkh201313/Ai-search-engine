import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'News — Lumen',
  description:
    'Live headlines from trusted sources, with weather and markets. Ask Lumen about any story to get a cited, researched answer.',
};

export default function NewsLayout({ children }: { children: React.ReactNode }) {
  return children;
}
