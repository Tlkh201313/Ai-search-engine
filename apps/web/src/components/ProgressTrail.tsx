'use client';

import { Check, Loader2 } from 'lucide-react';

import type { StageStatus } from '@/hooks/useResearch';
import { STAGE_LABELS, STAGE_ORDER } from '@/lib/modes';
import { cn } from '@/lib/utils';

interface Props {
  stageStatus: Record<string, StageStatus>;
  counts: { candidates?: number; readable?: number; reading?: number };
  subqueries: string[];
}

export function ProgressTrail({ stageStatus, counts, subqueries }: Props) {
  const detailFor = (stage: string): string | null => {
    if (stage === 'understanding' && subqueries.length)
      return `Exploring ${subqueries.length} related angle${subqueries.length > 1 ? 's' : ''}`;
    if (stage === 'finding_sources' && counts.candidates != null)
      return `${counts.candidates} candidate source${counts.candidates === 1 ? '' : 's'}`;
    if (stage === 'reading' && counts.readable != null)
      return `Read ${counts.readable} page${counts.readable === 1 ? '' : 's'}`;
    if (stage === 'reading' && counts.reading != null)
      return `Reading ${counts.reading} page${counts.reading === 1 ? '' : 's'}`;
    return null;
  };

  return (
    <ol className="space-y-1">
      {STAGE_ORDER.map((stage) => {
        const status = stageStatus[stage] ?? 'pending';
        const detail = detailFor(stage);
        return (
          <li key={stage} className="flex items-center gap-3 py-1">
            <span className="flex h-5 w-5 shrink-0 items-center justify-center">
              {status === 'done' ? (
                <span className="flex h-5 w-5 items-center justify-center rounded-full bg-accent/12">
                  <Check className="h-3 w-3 text-accent" />
                </span>
              ) : status === 'active' ? (
                <Loader2 className="h-[18px] w-[18px] animate-spin text-accent" />
              ) : (
                <span className="h-2 w-2 rounded-full bg-faint/40" />
              )}
            </span>
            <span
              className={cn(
                'text-sm transition-colors',
                status === 'active' && 'font-medium text-ink',
                status === 'done' && 'text-muted',
                status === 'pending' && 'text-faint',
              )}
            >
              {STAGE_LABELS[stage]}
            </span>
            {detail && (status === 'active' || status === 'done') && (
              <span className="ml-auto text-xs text-faint">{detail}</span>
            )}
          </li>
        );
      })}
    </ol>
  );
}
