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
    <div className="flex flex-col divide-y divide-line">
      {EXAMPLE_PROMPTS.map((ex) => {
        const Icon = MODE_MAP[ex.mode].icon;
        return (
          <button
            key={ex.q}
            type="button"
            onClick={() => onPick(ex.q, ex.mode)}
            className="group flex items-center gap-3 py-3 text-left transition-colors hover:text-accent"
          >
            <Icon className="h-4 w-4 shrink-0 text-faint transition-colors group-hover:text-accent" />
            <span className="flex-1 text-sm text-muted transition-colors group-hover:text-accent">
              {ex.q}
            </span>
            <ArrowUpRight className="h-4 w-4 shrink-0 text-faint opacity-0 transition-opacity group-hover:opacity-100" />
          </button>
        );
      })}
    </div>
  );
}
