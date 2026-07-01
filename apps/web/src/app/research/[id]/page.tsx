'use client';

import { useParams } from 'next/navigation';
import { useCallback, useEffect, useRef, useState } from 'react';

import { ChatInput } from '@/components/ChatInput';
import { Turn, type TurnData } from '@/components/Turn';
import type { ResearchState } from '@/hooks/useResearch';
import { ApiError, createResearch, type ConversationTurn } from '@/lib/api';
import { addRecent, takePending } from '@/lib/history';
import { DEFAULT_PERSONA } from '@/lib/personas';
import type { Persona, ResearchMode } from '@/lib/types';

interface TurnSummary {
  status: ResearchState['status'];
  query: string;
  answer: string;
}

export default function ResearchPage() {
  const params = useParams<{ id: string }>();
  const id = String(params.id);

  const [turns, setTurns] = useState<TurnData[]>([]);
  const [summaries, setSummaries] = useState<Record<string, TurnSummary>>({});
  const [mode, setMode] = useState<ResearchMode>('quick');
  const [persona, setPersona] = useState<Persona>(DEFAULT_PERSONA);
  const [busy, setBusy] = useState(false);
  const [followError, setFollowError] = useState<string | null>(null);

  // Refs mirror latest state so callbacks can read it without stale closures.
  const turnsRef = useRef(turns);
  turnsRef.current = turns;
  const summariesRef = useRef(summaries);
  summariesRef.current = summaries;
  const personaRef = useRef(persona);
  personaRef.current = persona;

  useEffect(() => {
    const pending = takePending(id);
    // Functional update: StrictMode re-runs this effect and takePending is
    // consume-once — never clobber an already-initialized thread for this id.
    setTurns((prev) => {
      if (prev.some((t) => t.id === id)) return prev;
      return [
        pending
          ? { id, query: pending.query, mode: pending.mode, live: true }
          : { id, query: '', mode: 'quick', live: false },
      ];
    });
    if (pending) {
      setMode(pending.mode);
      setPersona(pending.persona);
    }
  }, [id]);

  const handleState = useCallback((turnId: string, state: ResearchState) => {
    setSummaries((prev) => {
      const existing = prev[turnId];
      const answer = state.result?.answer?.summary || state.result?.answer?.detail || '';
      const query = state.result?.query ?? existing?.query ?? '';
      if (existing && existing.status === state.status && existing.answer === answer) {
        return prev;
      }
      return { ...prev, [turnId]: { status: state.status, query, answer } };
    });
  }, []);

  const handleFollowUp = useCallback(
    async (query: string, m: ResearchMode, p?: Persona) => {
      setBusy(true);
      setFollowError(null);
      const chosen = p ?? personaRef.current;
      // Build conversation context from completed prior turns (in order).
      const context: ConversationTurn[] = turnsRef.current
        .map((t) => {
          const s = summariesRef.current[t.id];
          return { query: s?.query || t.query, answer: s?.answer || '' };
        })
        .filter((c) => c.query && c.answer);
      try {
        const { id: newId } = await createResearch(query, m, chosen, context);
        addRecent({ id: newId, query, mode: m, ts: Date.now() });
        setTurns((prev) => [...prev, { id: newId, query, mode: m, live: true }]);
        setMode(m);
        setPersona(chosen);
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
    },
    [],
  );

  return (
    <div className="mx-auto flex min-h-dvh w-full max-w-3xl flex-col px-4 sm:px-6">
      <div className="flex-1 py-8">
        <div className="space-y-10">
          {turns.map((t) => (
            <Turn key={t.id} turn={t} onState={handleState} onFollowUp={handleFollowUp} />
          ))}
        </div>
      </div>

      {/* Sticky follow-up input */}
      <div className="sticky bottom-0 z-10">
        <div className="bg-gradient-to-t from-paper via-paper to-transparent pb-4 pt-8">
          {followError && (
            <p className="mb-2 text-center text-xs text-red-500">{followError}</p>
          )}
          <ChatInput
            onSubmit={handleFollowUp}
            mode={mode}
            onModeChange={setMode}
            persona={persona}
            onPersonaChange={setPersona}
            busy={busy}
          />
        </div>
      </div>
    </div>
  );
}
