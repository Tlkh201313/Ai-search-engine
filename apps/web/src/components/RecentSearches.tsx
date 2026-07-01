'use client';

import { Clock } from 'lucide-react';
import { useEffect, useState } from 'react';

import { clearRecent, getRecent, type RecentSearch } from '@/lib/history';
import { MODE_MAP } from '@/lib/modes';
import type { ResearchMode } from '@/lib/types';

export function RecentSearches({
  onPick,
}: {
  onPick: (query: string, mode: ResearchMode) => void;
}) {
  const [recent, setRecent] = useState<RecentSearch[]>([]);

  useEffect(() => {
    setRecent(getRecent());
  }, []);

  if (recent.length === 0) return null;

  return (
    <div>
      <div className="mb-2.5 flex items-center justify-between">
        <span className="flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-faint">
          <Clock className="h-3.5 w-3.5" />
          Recent
        </span>
        <button
          type="button"
          onClick={() => {
            clearRecent();
            setRecent([]);
          }}
          className="text-xs text-faint transition-colors hover:text-ink"
        >
          Clear
        </button>
      </div>
      <div className="flex flex-wrap gap-2">
        {recent.map((r) => {
          const Icon = MODE_MAP[r.mode]?.icon ?? Clock;
          return (
            <button
              key={r.id}
              type="button"
              onClick={() => onPick(r.query, r.mode)}
              className="chip max-w-full"
            >
              <Icon className="h-3.5 w-3.5 text-faint" />
              <span className="truncate">{r.query}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
