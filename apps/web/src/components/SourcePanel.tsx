'use client';

import { Library } from 'lucide-react';

import type { Source } from '@/lib/types';

import { SourceCard } from './SourceCard';
import { SourceCardSkeleton } from './Skeletons';

interface Props {
  sources: Source[];
  loading?: boolean;
  highlightId?: number | null;
  anchorPrefix?: string;
}

export function SourcePanel({ sources, loading, highlightId, anchorPrefix }: Props) {
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 text-sm font-medium text-ink">
        <Library className="h-4 w-4 text-faint" />
        Sources
        {sources.length > 0 && (
          <span className="rounded-full bg-ink/8 px-1.5 py-0.5 text-xs text-muted">
            {sources.length}
          </span>
        )}
      </div>

      {loading && sources.length === 0 ? (
        <div className="space-y-3">
          {[0, 1, 2].map((i) => (
            <SourceCardSkeleton key={i} />
          ))}
        </div>
      ) : sources.length === 0 ? (
        <p className="rounded-xl border border-dashed border-line px-4 py-6 text-center text-xs text-faint">
          Sources will appear here as they are found and ranked.
        </p>
      ) : (
        <div className="space-y-3">
          {sources.map((s) => (
            <SourceCard
              key={s.id}
              source={s}
              highlighted={highlightId === s.id}
              anchorPrefix={anchorPrefix}
            />
          ))}
        </div>
      )}
    </div>
  );
}
