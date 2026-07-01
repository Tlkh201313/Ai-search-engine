'use client';

import { Library } from 'lucide-react';
import { useParams } from 'next/navigation';
import { useCallback, useEffect, useRef, useState } from 'react';

import { ChatInput } from '@/components/ChatInput';
import { SourceDrawer } from '@/components/SourceDrawer';
import { SourcePanel } from '@/components/SourcePanel';
import { TopBar } from '@/components/TopBar';
import { Turn, type TurnData } from '@/components/Turn';
import type { ResearchState } from '@/hooks/useResearch';
import { ApiError, createResearch, type ConversationTurn } from '@/lib/api';
import { addRecent, takePending } from '@/lib/history';
import type { ResearchMode, Source } from '@/lib/types';

interface TurnSummary {
  sources: Source[];
  status: ResearchState['status'];
  query: string;
  answer: string;
}

export default function ResearchPage() {
  const params = useParams<{ id: string }>();
  const id = String(params.id);

  const [turns, setTurns] = useState<TurnData[]>([]);
  const [summaries, setSummaries] = useState<Record<string, TurnSummary>>({});
  const [activeTurnId, setActiveTurnId] = useState<string>(id);
  const [highlightId, setHighlightId] = useState<number | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [mode, setMode] = useState<ResearchMode>('quick');
  const [busy, setBusy] = useState(false);
  const [followError, setFollowError] = useState<string | null>(null);

  // Refs mirror latest state so callbacks can read it without stale closures.
  const turnsRef = useRef(turns);
  turnsRef.current = turns;
  const summariesRef = useRef(summaries);
  summariesRef.current = summaries;

  useEffect(() => {
    const pending = takePending(id);
    setTurns([
      pending
        ? { id, query: pending.query, mode: pending.mode, live: true }
        : { id, query: '', mode: 'quick', live: false },
    ]);
    setActiveTurnId(id);
    if (pending) setMode(pending.mode);
  }, [id]);

  const handleState = useCallback((turnId: string, state: ResearchState) => {
    setSummaries((prev) => {
      const existing = prev[turnId];
      const answer = state.result?.answer.summary ?? '';
      const query = state.result?.query ?? existing?.query ?? '';
      if (
        existing &&
        existing.status === state.status &&
        existing.sources === state.sources &&
        existing.answer === answer
      ) {
        return prev;
      }
      return {
        ...prev,
        [turnId]: { sources: state.sources, status: state.status, query, answer },
      };
    });
  }, []);

  const scrollToSource = useCallback((sid: number) => {
    const desktop = window.matchMedia('(min-width: 1024px)').matches;
    if (!desktop) setDrawerOpen(true);
    window.setTimeout(
      () => {
        const prefix = desktop ? 'desk' : 'draw';
        document
          .getElementById(`${prefix}-source-${sid}`)
          ?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      },
      desktop ? 0 : 90,
    );
  }, []);

  const handleCite = useCallback(
    (turnId: string, sid: number) => {
      setActiveTurnId(turnId);
      setHighlightId(sid);
      scrollToSource(sid);
      window.setTimeout(() => setHighlightId(null), 2200);
    },
    [scrollToSource],
  );

  const handleFollowUp = useCallback(async (query: string, m: ResearchMode) => {
    setBusy(true);
    setFollowError(null);
    // Build conversation context from completed prior turns (in order).
    const context: ConversationTurn[] = turnsRef.current
      .map((t) => {
        const s = summariesRef.current[t.id];
        return { query: s?.query || t.query, answer: s?.answer || '' };
      })
      .filter((c) => c.query && c.answer);
    try {
      const { id: newId } = await createResearch(query, m, context);
      addRecent({ id: newId, query, mode: m, ts: Date.now() });
      setTurns((prev) => [...prev, { id: newId, query, mode: m, live: true }]);
      setActiveTurnId(newId);
      setMode(m);
      window.setTimeout(
        () => window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' }),
        70,
      );
    } catch (err) {
      setFollowError(
        err instanceof ApiError ? err.message : "Couldn't reach the research API.",
      );
    } finally {
      setBusy(false);
    }
  }, []);

  const active = summaries[activeTurnId];
  const activeSources = active?.sources ?? [];
  const activeLoading = active?.status === 'running' || active?.status === 'connecting';

  return (
    <div className="flex min-h-dvh flex-col">
      <TopBar />

      <div className="mx-auto grid w-full max-w-6xl flex-1 gap-8 px-4 sm:px-6 lg:grid-cols-[minmax(0,1fr)_20rem]">
        {/* Conversation */}
        <div className="min-w-0 py-8">
          <div className="space-y-8">
            {turns.map((t) => (
              <Turn
                key={t.id}
                turn={t}
                onState={handleState}
                onCite={handleCite}
                onFollowUp={handleFollowUp}
              />
            ))}
          </div>

          {/* Sticky follow-up input */}
          <div className="sticky bottom-0 z-10 mt-6">
            <div className="bg-gradient-to-t from-paper via-paper to-transparent pb-4 pt-8">
              {followError && (
                <p className="mb-2 text-center text-xs text-red-500">{followError}</p>
              )}
              <ChatInput
                onSubmit={handleFollowUp}
                mode={mode}
                onModeChange={setMode}
                busy={busy}
              />
            </div>
          </div>
        </div>

        {/* Desktop source panel */}
        <aside className="hidden lg:block">
          <div className="scroll-slim sticky top-20 max-h-[calc(100dvh-6rem)] overflow-y-auto pb-8">
            <SourcePanel
              sources={activeSources}
              loading={activeLoading}
              highlightId={highlightId}
              anchorPrefix="desk"
            />
          </div>
        </aside>
      </div>

      {/* Mobile sources trigger */}
      {activeSources.length > 0 && (
        <button
          type="button"
          onClick={() => setDrawerOpen(true)}
          className="fixed bottom-28 right-4 z-30 flex items-center gap-2 rounded-full border border-line bg-raised px-4 py-2.5 text-sm font-medium text-ink shadow-float lg:hidden"
        >
          <Library className="h-4 w-4 text-accent" />
          {activeSources.length} sources
        </button>
      )}

      <SourceDrawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        sources={activeSources}
        highlightId={highlightId}
      />
    </div>
  );
}
