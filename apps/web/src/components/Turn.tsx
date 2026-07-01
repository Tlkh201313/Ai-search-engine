'use client';

import { AlertCircle, AlignLeft, RotateCw } from 'lucide-react';
import { useEffect, useState } from 'react';

import { useResearch, type ResearchState } from '@/hooks/useResearch';
import type { ResearchMode, Source } from '@/lib/types';
import { cn, faviconFor } from '@/lib/utils';

import { AnswerView } from './AnswerView';
import { ProgressTrail } from './ProgressTrail';
import { SourceCard } from './SourceCard';

export interface TurnData {
  id: string;
  query: string;
  mode: ResearchMode;
  live: boolean;
}

interface Props {
  turn: TurnData;
  onState: (id: string, state: ResearchState) => void;
  onFollowUp: (query: string, mode: ResearchMode) => void;
}

function SourceStrip({ sources, onMore }: { sources: Source[]; onMore: () => void }) {
  const shown = sources.slice(0, 4);
  const extra = sources.length - shown.length;
  return (
    <div className="mb-4 grid grid-cols-2 gap-2 sm:grid-cols-4">
      {shown.map((s) => (
        <a
          key={s.id}
          href={s.url}
          target="_blank"
          rel="noopener noreferrer"
          className="flex flex-col justify-between gap-1.5 rounded-lg bg-raised p-2.5 transition-colors hover:bg-ink/10"
        >
          <span className="line-clamp-2 text-xs leading-snug text-ink">{s.title}</span>
          <span className="flex items-center gap-1.5 text-[11px] text-faint">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={s.favicon ?? faviconFor(s.domain)}
              alt=""
              width={14}
              height={14}
              className="h-3.5 w-3.5 rounded-full"
            />
            <span className="truncate">{s.domain}</span>
            <span>· {s.id}</span>
          </span>
        </a>
      ))}
      {extra > 0 && (
        <button
          type="button"
          onClick={onMore}
          className="flex items-center justify-center rounded-lg bg-raised p-2.5 text-xs text-muted transition-colors hover:bg-ink/10"
        >
          +{extra} sources
        </button>
      )}
    </div>
  );
}

export function Turn({ turn, onState, onFollowUp }: Props) {
  const state = useResearch(turn.id, {
    live: turn.live,
    query: turn.query,
    mode: turn.mode,
  });
  const [tab, setTab] = useState<'answer' | 'sources'>('answer');
  const [highlightId, setHighlightId] = useState<number | null>(null);

  useEffect(() => {
    onState(turn.id, state);
  }, [state, turn.id, onState]);

  const query = state.result?.query || turn.query;
  const sources = state.sources;
  const showTrail = state.status !== 'error' && !state.answerText && !state.result;
  const failed = state.status === 'error' && !state.answerText;

  const onCite = (id: number) => {
    setTab('sources');
    setHighlightId(id);
    window.setTimeout(() => {
      document
        .getElementById(`t${turn.id}-source-${id}`)
        ?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }, 60);
    window.setTimeout(() => setHighlightId(null), 2200);
  };

  const tabBtn = (key: 'answer' | 'sources', label: React.ReactNode) => (
    <button
      type="button"
      onClick={() => setTab(key)}
      className={cn(
        'flex items-center gap-2 border-b-2 px-1 pb-2.5 text-sm font-medium transition-colors',
        tab === key
          ? 'border-accent text-ink'
          : 'border-transparent text-muted hover:text-ink',
      )}
    >
      {label}
    </button>
  );

  return (
    <article className="border-b border-line/70 pb-10 last:border-0">
      <h2 className="mb-4 text-[1.65rem] font-medium leading-snug tracking-tight text-ink">
        {query}
      </h2>

      {failed ? (
        <div className="flex items-start gap-3 rounded-xl border border-red-500/25 bg-red-500/5 p-4">
          <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-red-500" />
          <div className="flex-1">
            <p className="text-sm font-medium text-ink">Couldn&apos;t complete</p>
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
        <>
          <div className="mb-5 flex items-center gap-6 border-b border-line">
            {tabBtn(
              'answer',
              <>
                <AlignLeft className="h-4 w-4" />
                Answer
              </>,
            )}
            {sources.length > 0 &&
              tabBtn('sources', <>Sources · {sources.length}</>)}
          </div>

          {tab === 'answer' ? (
            <>
              {sources.length > 0 && (
                <SourceStrip sources={sources} onMore={() => setTab('sources')} />
              )}
              <AnswerView
                state={state}
                mode={state.result?.mode || turn.mode}
                onCite={onCite}
                onFollowUp={onFollowUp}
              />
            </>
          ) : (
            <div className="grid gap-3 sm:grid-cols-2">
              {sources.map((s) => (
                <SourceCard
                  key={s.id}
                  source={s}
                  highlighted={highlightId === s.id}
                  anchorPrefix={`t${turn.id}`}
                />
              ))}
            </div>
          )}
        </>
      )}
    </article>
  );
}
