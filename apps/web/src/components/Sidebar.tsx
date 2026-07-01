'use client';

import { Clock, Home, Library, Plus } from 'lucide-react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

import { createResearch } from '@/lib/api';
import {
  addRecent,
  getRecent,
  RECENT_EVENT,
  setPending,
  type RecentSearch,
} from '@/lib/history';
import { DEFAULT_PERSONA } from '@/lib/personas';
import { loadThread } from '@/lib/threads';
import { cn } from '@/lib/utils';

import { Brand, Logo } from './Brand';
import { ThemeToggle } from './ThemeToggle';

export function Sidebar() {
  const router = useRouter();
  const pathname = usePathname();
  const [recent, setRecent] = useState<RecentSearch[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const refresh = () => setRecent(getRecent());
    refresh();
    window.addEventListener(RECENT_EVENT, refresh);
    return () => window.removeEventListener(RECENT_EVENT, refresh);
  }, [pathname]);

  const open = async (r: RecentSearch) => {
    setError(null);
    // Saved thread: reopen it instantly from the local archive.
    if (r.threadId && loadThread(r.threadId)) {
      router.push(`/research/${r.threadId}`);
      return;
    }
    // No archive (old entry / cleared storage): re-run the query.
    try {
      const { id } = await createResearch(r.query, r.mode, DEFAULT_PERSONA);
      setPending(id, { query: r.query, mode: r.mode, persona: DEFAULT_PERSONA });
      addRecent({ id, query: r.query, mode: r.mode, ts: Date.now(), threadId: id });
      router.push(`/research/${id}`);
    } catch {
      setError("Can't reach the API — is the backend running?");
    }
  };

  return (
    <>
      {/* Mobile top bar */}
      <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-line bg-paper px-4 md:hidden">
        <Brand />
        <div className="flex items-center gap-1">
          <Link
            href="/"
            aria-label="New thread"
            className="flex h-9 w-9 items-center justify-center rounded-full text-muted hover:bg-ink/5 hover:text-ink"
          >
            <Plus className="h-5 w-5" />
          </Link>
          <ThemeToggle />
        </div>
      </header>

      {/* Desktop sidebar */}
      <aside className="sticky top-0 hidden h-dvh w-56 shrink-0 flex-col border-r border-line bg-raised md:flex">
        <div className="px-4 pb-2 pt-5">
          <Link href="/" className="flex items-center gap-2.5">
            <Logo className="h-8 w-8" />
            <span className="text-lg font-semibold tracking-tight text-ink">Lumen</span>
          </Link>
        </div>

        <div className="px-3 pt-3">
          <Link
            href="/"
            className="flex items-center gap-2 rounded-full border border-line bg-surface px-4 py-2.5 text-sm font-medium text-ink shadow-subtle transition-colors hover:border-accent/40"
          >
            <Plus className="h-4 w-4 text-muted" />
            New Thread
          </Link>
        </div>

        <nav className="mt-4 space-y-0.5 px-3">
          <Link
            href="/"
            className={cn(
              'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
              pathname === '/' ? 'bg-ink/5 text-ink' : 'text-muted hover:bg-ink/5 hover:text-ink',
            )}
          >
            <Home className="h-4 w-4" />
            Home
          </Link>
          <div className="flex items-center gap-3 px-3 pb-1 pt-3 text-sm font-medium text-muted">
            <Library className="h-4 w-4" />
            Library
          </div>
        </nav>

        <div className="scroll-slim min-h-0 flex-1 overflow-y-auto px-3 pb-3">
          {error && <p className="px-3 py-1 text-xs text-red-500">{error}</p>}
          {recent.length === 0 ? (
            <p className="px-3 py-1 text-xs text-faint">No threads yet</p>
          ) : (
            recent.map((r) => (
              <button
                key={r.id}
                type="button"
                onClick={() => open(r)}
                className="flex w-full items-center gap-2 rounded-lg px-3 py-1.5 text-left text-[13px] text-muted transition-colors hover:bg-ink/5 hover:text-ink"
              >
                <Clock className="h-3.5 w-3.5 shrink-0 text-faint" />
                <span className="truncate">{r.query}</span>
              </button>
            ))
          )}
        </div>

        <div className="flex items-center justify-between border-t border-line px-4 py-3">
          <span className="text-xs text-faint">Lumen</span>
          <ThemeToggle />
        </div>
      </aside>
    </>
  );
}
