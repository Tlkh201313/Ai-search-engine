'use client';

import type { Source } from '@/lib/types';
import { cn } from '@/lib/utils';

interface Props {
  id: number;
  source?: Source;
  onClick: () => void;
}

export function CitationChip({ id, source, onClick }: Props) {
  return (
    <button
      type="button"
      onClick={onClick}
      title={source ? `${source.title} — ${source.domain}` : `Source ${id}`}
      className={cn(
        'group/cite relative -translate-y-[3px] mx-0.5 inline-flex h-[18px] min-w-[18px] items-center justify-center',
        'rounded-[5px] border border-accent/25 bg-accent/10 px-1 align-baseline text-[11px]',
        'font-semibold leading-none text-accent transition-colors hover:bg-accent/20',
      )}
    >
      {id}
      {source && (
        <span className="pointer-events-none absolute bottom-full left-1/2 z-40 mb-1.5 hidden w-56 -translate-x-1/2 rounded-lg border border-line bg-raised p-2.5 text-left shadow-float group-hover/cite:block">
          <span className="flex items-center gap-1.5 text-[11px] font-medium text-faint">
            {source.domain}
          </span>
          <span className="mt-1 block text-xs font-medium leading-snug text-ink">
            {source.title}
          </span>
        </span>
      )}
    </button>
  );
}
