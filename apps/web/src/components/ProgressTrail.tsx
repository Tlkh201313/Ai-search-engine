'use client';

import { Check, ChevronDown, Loader2 } from 'lucide-react';
import { useState } from 'react';

import type { StageStatus } from '@/hooks/useResearch';
import { STAGE_LABELS, STAGE_ORDER } from '@/lib/modes';
import { cn } from '@/lib/utils';

interface Props {
  stageStatus: Record<string, StageStatus>;
  counts: { candidates?: number; readable?: number; reading?: number };
  subqueries: string[];
}

export function ProgressTrail({ stageStatus, counts, subqueries }: Props) {
  const [open, setOpen] = useState(false);

  const detailFor = (stage: string): string | null => {
    if (stage === 'understanding' && subqueries.length)
      return `${subqueries.length} angle${subqueries.length > 1 ? 's' : ''}`;
    if (stage === 'finding_sources' && counts.candidates != null)
      return `${counts.candidates} candidate${counts.candidates === 1 ? '' : 's'}`;
    if (stage === 'reading' && counts.readable != null)
      return `read ${counts.readable}`;
    if (stage === 'reading' && counts.reading != null)
      return `reading ${counts.reading}`;
    return null;
  };

  // Current active stage (or last done) drives the single-line summary.
  const activeStage =
    STAGE_ORDER.find((s) => stageStatus[s] === 'active') ??
    [...STAGE_ORDER].reverse().find((s) => stageStatus[s] === 'done') ??
    STAGE_ORDER[0];
  const done = STAGE_ORDER.filter((s) => stageStatus[s] === 'done').length;

  return (
    <div className="animate-fade-in">
      {/* Single-line, perplexity-style summary */}
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center gap-2.5 text-left"
      >
        <Loader2 className="h-4 w-4 shrink-0 animate-spin text-accent" />
        <span className="text-sm font-medium text-ink">{STAGE_LABELS[activeStage]}</span>
        {detailFor(activeStage) && (
          <span className="text-xs text-faint">· {detailFor(activeStage)}</span>
        )}
        <span className="ml-auto flex items-center gap-1.5 text-xs text-faint">
          {done}/{STAGE_ORDER.length}
          <ChevronDown className={cn('h-3.5 w-3.5 transition-transform', open && 'rotate-180')} />
        </span>
      </button>

      {/* Expanded: full step list */}
      {open && (
        <ol className="mt-3 space-y-1 border-t border-line pt-3">
          {STAGE_ORDER.map((stage) => {
            const status = stageStatus[stage] ?? 'pending';
            const detail = detailFor(stage);
            return (
              <li key={stage} className="flex items-center gap-3 py-0.5">
                <span className="flex h-4 w-4 shrink-0 items-center justify-center">
                  {status === 'done' ? (
                    <Check className="h-3.5 w-3.5 text-accent" />
                  ) : status === 'active' ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin text-accent" />
                  ) : (
                    <span className="h-1.5 w-1.5 rounded-full bg-faint/40" />
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
                {detail && status !== 'pending' && (
                  <span className="ml-auto text-xs text-faint">{detail}</span>
                )}
              </li>
            );
          })}
        </ol>
      )}
    </div>
  );
}
