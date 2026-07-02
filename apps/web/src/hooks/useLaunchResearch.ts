'use client';

import { useRouter } from 'next/navigation';
import { useState } from 'react';

import { createResearch } from '@/lib/api';
import { addRecent, setPending } from '@/lib/history';
import { DEFAULT_PERSONA } from '@/lib/personas';
import type { Persona, ResearchMode } from '@/lib/types';

/** Start a research thread from anywhere (news cards, tickers, shortcuts). */
export function useLaunchResearch() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const launch = async (
    query: string,
    mode: ResearchMode = 'quick',
    persona: Persona = DEFAULT_PERSONA,
  ): Promise<boolean> => {
    setBusy(true);
    setError(null);
    try {
      const { id } = await createResearch(query, mode, persona);
      setPending(id, { query, mode, persona });
      addRecent({ id, query, mode, ts: Date.now(), threadId: id });
      router.push(`/research/${id}`);
      return true;
    } catch {
      setError("Couldn't reach the research API. Is the backend running?");
      setBusy(false);
      return false;
    }
  };

  return { launch, busy, error };
}
