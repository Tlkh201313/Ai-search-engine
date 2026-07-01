'use client';

import { AlertCircle, RotateCw } from 'lucide-react';
import { useEffect } from 'react';

import { useResearch, type ResearchState } from '@/hooks/useResearch';
import { MODE_MAP } from '@/lib/modes';
import type { ResearchMode } from '@/lib/types';

import { AnswerView } from './AnswerView';
import { ProgressTrail } from './ProgressTrail';

export interface TurnData {
  id: string;
  query: string;
  mode: ResearchMode;
  live: boolean;
}

interface Props {
  turn: TurnData;
  onState: (id: string, state: ResearchState) => void;
  onCite: (turnId: string, id: number) => void;
  onFollowUp: (query: string, mode: ResearchMode) => void;
}

export function Turn({ turn, onState, onCite, onFollowUp }: Props) {
  const state = useResearch(turn.id, {
    live: turn.live,
    query: turn.query,
    mode: turn.mode,
  });

  useEffect(() => {
    onState(turn.id, state);
  }, [state, turn.id, onState]);

  const query = state.result?.query || turn.query;
  const mode = state.result?.mode || turn.mode;
  const ModeIcon = MODE_MAP[mode].icon;
  const showTrail = state.status !== 'error' && !state.answerText && !state.result;
  const failed = state.status === 'error' && !state.answerText;

  return (
    <article className="border-b border-line/70 pb-8 last:border-0">
      {/* Question */}
      <div className="mb-4 flex items-start gap-2.5">
        <h2 className="font-serif text-2xl font-medium leading-snug tracking-tight text-ink">
          {query}
        </h2>
      </div>
      <div className="mb-6 flex items-center gap-1.5 text-xs text-faint">
        <ModeIcon className="h-3.5 w-3.5" />
        {MODE_MAP[mode].label}
      </div>

      {failed ? (
        <div className="flex items-start gap-3 rounded-xl border border-red-500/25 bg-red-500/5 p-4">
          <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-red-500" />
          <div className="flex-1">
            <p className="text-sm font-medium text-ink">Research couldn&apos;t complete</p>
            <p className="mt-1 text-sm text-muted">{state.error}</p>
            <button
              type="button"
              onClick={() => onFollowUp(turn.query, turn.mode)}
              className="btn-ghost mt-3 !px-3 !py-1.5 text-accent"
            >
              <RotateCw className="h-3.5 w-3.5" />
              Try again
            </button>
          </div>
        </div>
      ) : showTrail ? (
        <div className="rounded-xl border border-line bg-surface p-5 animate-fade-in">
          <ProgressTrail
            stageStatus={state.stageStatus}
            counts={state.counts}
            subqueries={state.subqueries}
          />
        </div>
      ) : (
        <AnswerView
          state={state}
          mode={mode}
          onCite={(id) => onCite(turn.id, id)}
          onFollowUp={onFollowUp}
        />
      )}
    </article>
  );
}
