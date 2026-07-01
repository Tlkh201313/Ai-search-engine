'use client';

import { useEffect, useRef, useState } from 'react';

import { ApiError, getResearch, openResearchStream } from '@/lib/api';
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
  chat: boolean;
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
  chat: false,
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
  // Streaming deltas are buffered and flushed on a timer: re-rendering the
  // markdown tree per token is the main UI cost while an answer streams.
  const deltaBufRef = useRef('');
  const flushTimerRef = useRef<number | null>(null);

  useEffect(() => {
    if (startedRef.current) return;
    startedRef.current = true;
    let close: (() => void) | undefined;

    if (!opts.live) {
      // Reloaded / shared link: load the finished result.
      getResearch(id)
        .then((result) => {
          setState((s) => ({
            ...s,
            status: result.status === 'error' ? 'error' : 'complete',
            stage: 'done',
            progress: 1,
            sources: result.sources ?? [],
            result,
            answerText: result.answer?.detail ?? '',
            error: result.error,
            stageStatus: Object.fromEntries(STAGE_ORDER.map((st) => [st, 'done'])),
          }));
        })
        .catch((err: Error) => {
          if (err instanceof ApiError && err.status === 202) {
            // Still running — re-attach to the live stream instead.
            close = attach();
            return;
          }
          setState((s) => ({
            ...s,
            status: 'error',
            error:
              err.message ||
              'This research session has expired. Run the query again to refresh it.',
          }));
        });
      return () => close?.();
    }

    close = attach();
    return () => close?.();

    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  function attach() {
    const flush = () => {
      flushTimerRef.current = null;
      const chunk = deltaBufRef.current;
      if (!chunk) return;
      deltaBufRef.current = '';
      setState((prev) => ({ ...prev, status: 'running', answerText: prev.answerText + chunk }));
    };

    const closeStream = openResearchStream(id, {
      onEvent: (event) => {
        if (event.data?.heartbeat) return;
        if (event.data?.delta && !event.data?.result) {
          deltaBufRef.current += event.data.delta;
          if (flushTimerRef.current == null)
            flushTimerRef.current = window.setTimeout(flush, 80);
          return;
        }
        setState((prev) => {
          // Merge any buffered deltas so ordering is preserved.
          let answerText = prev.answerText;
          if (deltaBufRef.current) {
            answerText += deltaBufRef.current;
            deltaBufRef.current = '';
          }
          const next: ResearchState = {
            ...prev,
            answerText,
            status: 'running',
            stage: event.stage,
            message: event.message || prev.message,
            progress: Math.max(prev.progress, event.progress || 0),
            stageStatus: advanceStages(prev.stageStatus, event.stage, event.status),
          };
          if (event.data?.chat) next.chat = true;
          if (event.data?.subqueries) next.subqueries = event.data.subqueries;
          if (typeof event.data?.candidates === 'number')
            next.counts = { ...next.counts, candidates: event.data.candidates };
          if (typeof event.data?.reading === 'number')
            next.counts = { ...next.counts, reading: event.data.reading };
          if (typeof event.data?.readable === 'number')
            next.counts = { ...next.counts, readable: event.data.readable };
          if (event.data?.sources) next.sources = event.data.sources;
          if (event.data?.result) {
            const result = event.data.result;
            next.result = result;
            next.sources = result.sources.length ? result.sources : next.sources;
            next.answerText = result.answer?.detail || next.answerText;
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

    return () => {
      if (flushTimerRef.current != null) window.clearTimeout(flushTimerRef.current);
      closeStream();
    };
  }

  return state;
}
