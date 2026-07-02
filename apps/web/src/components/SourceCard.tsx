'use client';

import { ExternalLink } from 'lucide-react';
import { useState } from 'react';

import type { Source } from '@/lib/types';
import { cn, faviconFor, formatDate, relativeTime } from '@/lib/utils';

function RelevanceBar({ score }: { score: number }) {
  const pct = Math.round(Math.max(0, Math.min(1, score)) * 100);
  return (
    <div className="flex items-center gap-1.5" title={`Relevance ${pct}%`}>
      <div className="h-1 w-14 overflow-hidden rounded-full bg-ink/10">
        <div className="h-full rounded-full bg-accent/70" style={{ width: `${pct}%` }} />
      </div>
      <span className="text-[10px] tabular-nums text-faint">{pct}%</span>
    </div>
  );
}

export function SourceCard({
  source,
  highlighted,
  anchorPrefix = '',
}: {
  source: Source;
  highlighted?: boolean;
  anchorPrefix?: string;
}) {
  const [imgOk, setImgOk] = useState(true);
  const published = formatDate(source.published_at);
  const fetched = relativeTime(source.fetched_at);
  const anchorId = anchorPrefix ? `${anchorPrefix}-source-${source.id}` : `source-${source.id}`;

  return (
    <a
      id={anchorId}
      href={source.url}
      target="_blank"
      rel="noopener noreferrer"
      className={cn(
        'group block scroll-mt-20 rounded-xl border border-line bg-surface p-3.5 transition-all',
        'hover:border-accent/40 hover:shadow-card',
        highlighted && 'border-accent/60 ring-2 ring-accent/30',
      )}
    >
      <div className="flex items-center gap-2">
        <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-md bg-accent/12 text-[11px] font-semibold text-accent">
          {source.id}
        </span>
        {imgOk ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={source.favicon ?? faviconFor(source.domain)}
            alt=""
            width={16}
            height={16}
            className="h-4 w-4 rounded"
            onError={() => setImgOk(false)}
          />
        ) : (
          <span className="h-4 w-4 rounded bg-ink/10" />
        )}
        <span className="truncate text-xs font-medium text-muted">{source.domain}</span>
        {source.used && (
          <span
            className="ml-auto h-1.5 w-1.5 shrink-0 rounded-full bg-accent"
            title="Cited in the answer"
          />
        )}
        <ExternalLink
          className={cn(
            'h-3.5 w-3.5 text-faint opacity-0 transition-opacity group-hover:opacity-100',
            source.used ? 'ml-1.5' : 'ml-auto',
          )}
        />
      </div>

      <h4 className="mt-2 line-clamp-2 text-sm font-medium leading-snug text-ink group-hover:text-accent">
        {source.title}
      </h4>

      {source.snippet && (
        <p className="mt-1.5 line-clamp-2 text-xs leading-relaxed text-muted">
          {source.snippet}
        </p>
      )}

      <div className="mt-2.5 flex items-center justify-between gap-2">
        <RelevanceBar score={source.scores.overall} />
        <span className="text-[10px] text-faint">{published ?? fetched ?? ''}</span>
      </div>
    </a>
  );
}
