'use client';

import { useRouter } from 'next/navigation';
import { useState } from 'react';

import { ExamplePrompts } from '@/components/ExamplePrompts';
import { RecentSearches } from '@/components/RecentSearches';
import { SearchBar } from '@/components/SearchBar';
import { StatusNotice } from '@/components/StatusNotice';
import { TopBar } from '@/components/TopBar';
import { ApiError, createResearch } from '@/lib/api';
import { addRecent, setPending } from '@/lib/history';
import { DEFAULT_PERSONA } from '@/lib/personas';
import type { Persona, ResearchMode } from '@/lib/types';

export default function HomePage() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const start = async (query: string, mode: ResearchMode, persona: Persona = DEFAULT_PERSONA) => {
    setBusy(true);
    setError(null);
    try {
      const { id } = await createResearch(query, mode, persona);
      setPending(id, { query, mode, persona });
      addRecent({ id, query, mode, ts: Date.now() });
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
    <div className="flex min-h-dvh flex-col">
      <TopBar showNew={false} />

      <main className="mx-auto flex w-full max-w-content flex-1 flex-col justify-center px-4 py-10 sm:px-6 sm:py-16">
        <div className="mx-auto w-full max-w-2xl">
          <div className="mb-8 text-center sm:mb-10">
            <h1 className="font-serif text-[2.1rem] font-medium leading-tight tracking-tight text-ink sm:text-5xl">
              Ask anything.
              <br className="hidden sm:block" />
              <span className="text-muted"> Get a grounded answer.</span>
            </h1>
            <p className="mx-auto mt-4 max-w-md text-[15px] leading-relaxed text-muted">
              Lumen searches the web, reads the sources, weighs the evidence, and answers with
              real, clickable citations.
            </p>
          </div>

          <SearchBar onSubmit={start} busy={busy} />

          {error && (
            <p className="mt-3 text-center text-sm text-red-500">{error}</p>
          )}

          <div className="mt-4">
            <StatusNotice />
          </div>

          <div className="mt-10 space-y-8">
            <RecentSearches onPick={start} />
            <div>
              <p className="mb-3 text-xs font-medium uppercase tracking-wide text-faint">
                Try an example
              </p>
              <ExamplePrompts onPick={start} />
            </div>
          </div>
        </div>
      </main>

      <footer className="border-t border-line/60 py-5 text-center text-xs text-faint">
        Lumen · a grounded AI research engine · answers are only as good as their sources
      </footer>
    </div>
  );
}
