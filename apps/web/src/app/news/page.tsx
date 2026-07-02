'use client';

import { RotateCw } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';

import { MarketsCard } from '@/components/news/MarketsCard';
import { NewsCard } from '@/components/news/NewsCard';
import { WeatherCard } from '@/components/news/WeatherCard';
import { useLaunchResearch } from '@/hooks/useLaunchResearch';
import { fetchNews, NEWS_CATEGORIES, type NewsItem } from '@/lib/news';
import { cn } from '@/lib/utils';

function greeting(): string {
  const h = new Date().getHours();
  if (h < 5) return 'Up late?';
  if (h < 12) return 'Good morning.';
  if (h < 18) return 'Good afternoon.';
  return 'Good evening.';
}

export default function NewsPage() {
  const [category, setCategory] = useState('top');
  const [items, setItems] = useState<NewsItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [today, setToday] = useState('');
  const [hello, setHello] = useState('');
  const { launch, busy, error: launchError } = useLaunchResearch();

  useEffect(() => {
    setToday(
      new Date().toLocaleDateString(undefined, { day: 'numeric', month: 'long' }),
    );
    setHello(greeting());
  }, []);

  const load = useCallback(async (cat: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchNews(cat, 25);
      setItems(data.items);
    } catch {
      setError("Couldn't load the news. Is the backend running?");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load(category);
  }, [category, load]);

  // Hero = first story with an image; everything else flows into the grid.
  const heroIndex = items.findIndex((i) => i.image);
  const hero = heroIndex >= 0 ? items[heroIndex] : null;
  const rest = hero ? items.filter((_, i) => i !== heroIndex) : items;

  return (
    <div className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-6">
      {/* Header */}
      <header className="animate-slide-up">
        <p className="text-sm font-medium text-muted">{today}</p>
        <div className="mt-0.5 flex items-center justify-between gap-4">
          <h1 className="text-2xl font-semibold tracking-tight text-ink sm:text-3xl">
            {hello || ' '}
          </h1>
          <button
            type="button"
            onClick={() => void load(category)}
            disabled={loading}
            className="btn-ghost rounded-full"
            aria-label="Refresh stories"
          >
            <RotateCw className={cn('h-4 w-4', loading && 'animate-spin')} />
            <span className="hidden sm:inline">Refresh</span>
          </button>
        </div>
      </header>

      {(error || launchError) && (
        <p className="mt-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-600 dark:border-red-900 dark:bg-red-950/40 dark:text-red-400">
          {error || launchError}
        </p>
      )}

      <div className="mt-6 flex flex-col gap-6 lg:flex-row">
        {/* Widget rail */}
        <aside
          className="flex w-full shrink-0 flex-col gap-4 animate-slide-up lg:w-72"
          style={{ animationDelay: '60ms' }}
        >
          <WeatherCard />
          <MarketsCard />
        </aside>

        {/* Stories */}
        <section className="min-w-0 flex-1">
          <div className="scroll-slim -mx-1 flex gap-2 overflow-x-auto px-1 pb-3">
            {NEWS_CATEGORIES.map((c) => (
              <button
                key={c.key}
                type="button"
                onClick={() => setCategory(c.key)}
                className={cn(
                  'shrink-0 rounded-full px-3.5 py-1.5 text-sm font-medium transition-colors',
                  category === c.key
                    ? 'bg-accent text-white shadow-subtle'
                    : 'border border-line bg-surface text-muted hover:border-accent/40 hover:text-ink',
                )}
              >
                {c.label}
              </button>
            ))}
          </div>

          {loading ? (
            <div className="space-y-4">
              <div className="skeleton aspect-[16/8] rounded-2xl" />
              <div className="grid gap-4 sm:grid-cols-2">
                {Array.from({ length: 4 }).map((_, i) => (
                  <div key={i} className="skeleton h-64 rounded-2xl" />
                ))}
              </div>
            </div>
          ) : (
            <div className="space-y-4 animate-fade-in">
              {hero && <NewsCard item={hero} onAsk={(q) => void launch(q)} asking={busy} hero />}
              <div className="grid gap-4 sm:grid-cols-2">
                {rest.map((item) => (
                  <NewsCard
                    key={item.url}
                    item={item}
                    onAsk={(q) => void launch(q)}
                    asking={busy}
                  />
                ))}
              </div>
              {items.length === 0 && !error && (
                <p className="py-12 text-center text-sm text-muted">
                  No stories right now — try refreshing.
                </p>
              )}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
