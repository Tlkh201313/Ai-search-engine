'use client';

import { ArrowRight, Newspaper } from 'lucide-react';
import Link from 'next/link';
import { useEffect, useState } from 'react';

import { fetchNews, type NewsItem } from '@/lib/news';
import { relativeTime } from '@/lib/utils';

/** Compact live-headlines strip for the home page. Hidden if the API is down. */
export function NewsTicker() {
  const [items, setItems] = useState<NewsItem[] | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchNews('top', 4)
      .then((data) => !cancelled && setItems(data.items.slice(0, 3)))
      .catch(() => !cancelled && setItems(null));
    return () => {
      cancelled = true;
    };
  }, []);

  if (!items || items.length === 0) return null;

  return (
    <div className="card overflow-hidden animate-fade-in">
      <Link
        href="/news"
        className="group flex items-center justify-between border-b border-line px-4 py-2.5 transition-colors hover:bg-ink/[0.03]"
      >
        <span className="flex items-center gap-2 text-sm font-semibold text-ink">
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-accent opacity-60" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-accent" />
          </span>
          <Newspaper className="h-4 w-4 text-muted" />
          Today&apos;s news
        </span>
        <span className="flex items-center gap-1 text-xs font-medium text-muted transition-colors group-hover:text-accent">
          Open news
          <ArrowRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" />
        </span>
      </Link>

      <div className="divide-y divide-line">
        {items.map((item) => {
          const time = relativeTime(item.published_at);
          return (
            <a
              key={item.url}
              href={item.url}
              target="_blank"
              rel="noopener noreferrer"
              className="group flex items-baseline gap-2 px-4 py-2 transition-colors hover:bg-ink/[0.03]"
            >
              <span className="shrink-0 text-xs font-medium text-accent">{item.source}</span>
              <span className="truncate text-sm text-muted transition-colors group-hover:text-ink">
                {item.title}
              </span>
              {time && <span className="ml-auto shrink-0 text-[11px] text-faint">{time}</span>}
            </a>
          );
        })}
      </div>
    </div>
  );
}
