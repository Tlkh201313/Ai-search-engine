'use client';

import { useEffect, useRef, useState } from 'react';

import { getResearch, openResearchStream } from '@/lib/api';
import { STAGE_ORDER } from '@/lib/modes';
import type {
  ProgressStage,
  ResearchMode,
  ResearchResult,
  Source,
} from '@/lib/types';

export type StageStatus = 'pending' | 'active' | 'done';

export interface ResearchState {
  status: 'connecting' | 'running' | 'complete' | 'error';
  stage: ProgressStage;
  message: string;
  progress: number;
  subqueries: string[];
  counts: { candidates?: number; readable?: number; reading?: number };
  sources: Source[];
  answerText: string;
  result: ResearchResult | null;
  error: string | null;
  stageStatus: Record<string, StageStatus>;
}

const initialState = (): ResearchState => ({
  status: 'connecting',
  stage: 'understanding',
  message: 'Starting research…',
  progress: 0,
  subqueries: [],
  counts: {},
  sources: [],
  answerText: '',
  result: null,
  error: null,
  stageStatus: Object.fromEntries(STAGE_ORDER.map((s) => [s, 'pending'])),
});

function advanceStages(
  current: Record<string, StageStatus>,
  stage: ProgressStage,
  status: string,
): Record<string, StageStatus> {
  const idx = STAGE_ORDER.indexOf(stage);
  if (idx === -1) return current;
  const next = { ...current };
  for (let i = 0; i < idx; i++) next[STAGE_ORDER[i]] = 'done';
  next[stage] = status === 'done' ? 'done' : 'active';
  return next;
}

export function useResearch(
  id: string,
  opts: { live: boolean; query: string; mode: ResearchMode },
): ResearchState {
  const [state, setState] = useState<ResearchState>(initialState);
  const startedRef = useRef(false);

  useEffect(() => {
    if (startedRef.current) return;
    startedRef.current = true;

    if (!opts.live) {
      // Reloaded / shared link: load the finished result.
      getResearch(id)
        .then((result) => {
          setState((s) => ({
            ...s,
            status: result.status === 'error' ? 'error' : 'complete',
            stage: 'done',
            progress: 1,
            sources: result.sources,
            result,
            answerText: result.answer.detail,
            error: result.error,
            stageStatus: Object.fromEntries(STAGE_ORDER.map((st) => [st, 'done'])),
          }));
        })
        .catch((err: Error) => {
          setState((s) => ({
            ...s,
            status: 'error',
            error:
              err.message ||
              'This research session has expired. Run the query again to refresh it.',
          }));
        });
      return;
    }

    const close = openResearchStream(id, {
      onEvent: (event) => {
        setState((prev) => {
          if (event.data?.heartbeat) return prev;
          const next: ResearchState = {
            ...prev,
            status: 'running',
            stage: event.stage,
            message: event.message || prev.message,
            progress: Math.max(prev.progress, event.progress || 0),
            stageStatus: advanceStages(prev.stageStatus, event.stage, event.status),
          };
          if (event.data?.subqueries) next.subqueries = event.data.subqueries;
          if (typeof event.data?.candidates === 'number')
            next.counts = { ...next.counts, candidates: event.data.candidates };
          if (typeof event.data?.reading === 'number')
            next.counts = { ...next.counts, reading: event.data.reading };
          if (typeof event.data?.readable === 'number')
            next.counts = { ...next.counts, readable: event.data.readable };
          if (event.data?.sources) next.sources = event.data.sources;
          if (event.data?.delta) next.answerText = prev.answerText + event.data.delta;
          if (event.data?.result) {
            const result = event.data.result;
            next.result = result;
            next.sources = result.sources.length ? result.sources : next.sources;
            next.answerText = result.answer.detail || next.answerText;
            next.status = result.status === 'error' ? 'error' : 'complete';
            next.error = result.error;
            if (event.stage === 'done')
              next.stageStatus = Object.fromEntries(
                STAGE_ORDER.map((st) => [st, 'done']),
              );
          }
          return next;
        });
      },
      onError: (err) => {
        setState((prev) =>
          prev.status === 'complete'
            ? prev
            : { ...prev, status: 'error', error: err.message },
        );
      },
    });

    return close;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  return state;
}
