'use client';

import { ArrowUpRight } from 'lucide-react';

import { EXAMPLE_PROMPTS, MODE_MAP } from '@/lib/modes';
import type { ResearchMode } from '@/lib/types';

export function ExamplePrompts({
  onPick,
}: {
  onPick: (query: string, mode: ResearchMode) => void;
}) {
  return (
    <div className="grid gap-2.5 sm:grid-cols-2">
      {EXAMPLE_PROMPTS.map((ex) => {
        const Icon = MODE_MAP[ex.mode].icon;
        return (
          <button
            key={ex.q}
            type="button"
            onClick={() => onPick(ex.q, ex.mode)}
            className="group flex items-start gap-3 rounded-xl border border-line bg-surface p-3.5 text-left transition-all hover:border-accent/40 hover:shadow-subtle"
          >
            <Icon className="mt-0.5 h-4 w-4 shrink-0 text-faint transition-colors group-hover:text-accent" />
            <span className="flex-1 text-sm leading-snug text-ink">{ex.q}</span>
            <ArrowUpRight className="h-4 w-4 shrink-0 text-faint opacity-0 transition-opacity group-hover:opacity-100" />
          </button>
        );
      })}
    </div>
  );
}
