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

function restoredState(result: ResearchResult): ResearchState {
  return {
    ...initialState(),
    status: result.status === 'error' ? 'error' : 'complete',
    stage: 'done',
    progress: 1,
    sources: result.sources ?? [],
    result,
    answerText: result.answer?.detail ?? '',
    error: result.error,
    chat: (result.sources ?? []).length === 0,
    stageStatus: Object.fromEntries(STAGE_ORDER.map((st) => [st, 'done'])),
  };
}

export function useResearch(
  id: string,
  opts: { live: boolean; query: string; mode: ResearchMode; saved?: ResearchResult },
): ResearchState {
  const [state, setState] = useState<ResearchState>(() =>
    opts.saved ? restoredState(opts.saved) : initialState(),
  );
  const savedRef = useRef(!!opts.saved);
  // Streaming deltas are buffered and flushed on a timer: re-rendering the
  // markdown tree per token is the main UI cost while an answer streams.
  const deltaBufRef = useRef('');
  const flushTimerRef = useRef<number | null>(null);
  const liveRef = useRef(opts.live);
  liveRef.current = opts.live;

  // The effect must survive StrictMode's mount→cleanup→mount cycle: cleanup
  // closes the stream, so the re-run has to open a fresh one (the backend
  // replays buffered events, so re-attaching is lossless).
  useEffect(() => {
    if (savedRef.current) return; // restored from the local archive — nothing to fetch
    let cancelled = false;
    let close: (() => void) | undefined;

    const attach = () => {
      const flush = () => {
        flushTimerRef.current = null;
        const chunk = deltaBufRef.current;
        if (!chunk) return;
        deltaBufRef.current = '';
        setState((prev) => ({
          ...prev,
          status: 'running',
          answerText: prev.answerText + chunk,
        }));
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
        if (flushTimerRef.current != null) {
          window.clearTimeout(flushTimerRef.current);
          flushTimerRef.current = null;
        }
        closeStream();
      };
    };

    if (liveRef.current) {
      close = attach();
    } else {
      // Reloaded / shared link: load the finished result.
      getResearch(id)
        .then((result) => {
          if (cancelled) return;
          setState((s) => ({
            ...s,
            status: result.status === 'error' ? 'error' : 'complete',
            stage: 'done',
            progress: 1,
            sources: result.sources ?? [],
            result,
            answerText: result.answer?.detail ?? '',
            error: result.error,
            chat: (result.sources ?? []).length === 0,
            stageStatus: Object.fromEntries(STAGE_ORDER.map((st) => [st, 'done'])),
          }));
        })
        .catch((err: Error) => {
          if (cancelled) return;
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
    }

    return () => {
      cancelled = true;
      close?.();
    };
  }, [id]);

  return state;
}
