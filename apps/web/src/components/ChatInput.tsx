'use client';

import { ArrowUp } from 'lucide-react';
import { useRef, useState } from 'react';

import type { Persona, ResearchMode } from '@/lib/types';
import { cn } from '@/lib/utils';

import { ModeSelector } from './ModeSelector';
import { PersonaSelector } from './PersonaSelector';

interface Props {
  onSubmit: (query: string, mode: ResearchMode, persona: Persona) => void;
  mode: ResearchMode;
  onModeChange: (mode: ResearchMode) => void;
  persona: Persona;
  onPersonaChange: (persona: Persona) => void;
  busy?: boolean;
}

export function ChatInput({
  onSubmit,
  mode,
  onModeChange,
  persona,
  onPersonaChange,
  busy,
}: Props) {
  const [query, setQuery] = useState('');
  const ref = useRef<HTMLTextAreaElement>(null);

  const grow = () => {
    const el = ref.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  };

  const submit = () => {
    const trimmed = query.trim();
    if (trimmed.length < 2 || busy) return;
    onSubmit(trimmed, mode, persona);
    setQuery('');
    if (ref.current) ref.current.style.height = 'auto';
  };

  const canSubmit = query.trim().length >= 2 && !busy;

  return (
    <div className="rounded-3xl border border-line bg-surface shadow-card transition-all focus-within:border-accent/40 focus-within:shadow-float focus-within:ring-4 focus-within:ring-accent/10">
      <textarea
        ref={ref}
        value={query}
        rows={1}
        placeholder="Ask a follow-up…"
        onChange={(e) => {
          setQuery(e.target.value);
          grow();
        }}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            submit();
          }
        }}
        className="scroll-slim max-h-[160px] w-full resize-none bg-transparent px-4 pt-3.5 text-[15px] leading-relaxed text-ink outline-none placeholder:text-faint"
      />
      <div className="flex items-center justify-between gap-2 px-3 pb-3 pt-1">
        <div className="flex flex-wrap items-center gap-2">
          <ModeSelector value={mode} onChange={onModeChange} direction="up" />
          <PersonaSelector value={persona} onChange={onPersonaChange} direction="up" />
        </div>
        <button
          type="button"
          onClick={submit}
          disabled={!canSubmit}
          aria-label="Send"
          className={cn(
            'flex h-9 w-9 items-center justify-center rounded-full transition-all',
            canSubmit ? 'bg-accent text-white hover:bg-accent/90 hover:scale-105' : 'bg-ink/8 text-faint',
          )}
        >
          <ArrowUp className="h-[18px] w-[18px]" />
        </button>
      </div>
    </div>
  );
}
