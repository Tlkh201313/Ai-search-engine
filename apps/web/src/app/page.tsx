'use client';

import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

import { ExamplePrompts } from '@/components/ExamplePrompts';
import { SearchBar } from '@/components/SearchBar';
import { StatusNotice } from '@/components/StatusNotice';
import { ApiError, createResearch } from '@/lib/api';
import { addRecent, setPending } from '@/lib/history';
import { DEFAULT_PERSONA } from '@/lib/personas';
import type { Persona, ResearchMode } from '@/lib/types';

function greeting(): string {
  const h = new Date().getHours();
  if (h < 5) return 'Up late?';
  if (h < 12) return 'Good morning.';
  if (h < 18) return 'Good afternoon.';
  return 'Good evening.';
}

export default function HomePage() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hello, setHello] = useState('');
  useEffect(() => setHello(greeting()), []);

  const start = async (query: string, mode: ResearchMode, persona: Persona = DEFAULT_PERSONA) => {
    setBusy(true);
    setError(null);
    try {
      const { id } = await createResearch(query, mode, persona);
      setPending(id, { query, mode, persona });
      addRecent({ id, query, mode, ts: Date.now(), threadId: id });
      router.push(`/research/${id}`);
    } catch (err) {
      const message =
        err instanceof ApiError
          ? `Couldn't start research: ${err.message}`
          : "Couldn't reach the research API. Is the backend running?";
      setError(message);
      setBusy(false);
    }
  };

  return (
    <div className="flex min-h-[calc(100dvh-3.5rem)] flex-col md:min-h-dvh">
      <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col justify-center px-4 py-10 sm:px-6">
        <h1 className="mb-2 bg-gradient-to-r from-ink via-accent to-ink bg-clip-text text-center text-3xl font-medium tracking-tight text-transparent animate-slide-up sm:text-4xl">
          lumen
        </h1>
        <p className="mb-8 min-h-[1.5rem] text-center text-[15px] text-muted animate-slide-up" style={{ animationDelay: '40ms' }}>
          {hello} Ask anything — chat instantly or research with citations.
        </p>

        <div className="animate-slide-up" style={{ animationDelay: '80ms' }}>
          <SearchBar onSubmit={start} busy={busy} />
        </div>

        {error && <p className="mt-3 text-center text-sm text-red-500">{error}</p>}

        <div className="mt-4">
          <StatusNotice />
        </div>

        <div className="mt-8">
          <ExamplePrompts onPick={start} />
        </div>
      </main>
    </div>
  );
}
