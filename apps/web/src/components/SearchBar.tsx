'use client';

import { ArrowUp, Search } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';

import { DEFAULT_PERSONA } from '@/lib/personas';
import type { Persona, ResearchMode } from '@/lib/types';
import { cn } from '@/lib/utils';

import { ModeSelector } from './ModeSelector';
import { PersonaSelector } from './PersonaSelector';

interface Props {
  onSubmit: (query: string, mode: ResearchMode, persona: Persona) => void;
  initialMode?: ResearchMode;
  initialPersona?: Persona;
  initialQuery?: string;
  autoFocus?: boolean;
  busy?: boolean;
}

export function SearchBar({
  onSubmit,
  initialMode = 'quick',
  initialPersona = DEFAULT_PERSONA,
  initialQuery = '',
  autoFocus = true,
  busy = false,
}: Props) {
  const [query, setQuery] = useState(initialQuery);
  const [mode, setMode] = useState<ResearchMode>(initialMode);
  const [persona, setPersona] = useState<Persona>(initialPersona);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (autoFocus) textareaRef.current?.focus();
  }, [autoFocus]);

  // "/" focuses the search field from anywhere.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const el = document.activeElement;
      const typing = el instanceof HTMLInputElement || el instanceof HTMLTextAreaElement;
      if (e.key === '/' && !typing) {
        e.preventDefault();
        textareaRef.current?.focus();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  const grow = () => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 220)}px`;
  };

  const submit = () => {
    const trimmed = query.trim();
    if (trimmed.length < 2 || busy) return;
    onSubmit(trimmed, mode, persona);
  };

  const canSubmit = query.trim().length >= 2 && !busy;

  return (
    <div className="w-full">
      <div
        className={cn(
          'group relative rounded-2xl border border-line bg-surface shadow-card transition-shadow',
          'focus-within:border-accent/40 focus-within:shadow-float',
        )}
      >
        <div className="flex items-start gap-3 px-4 pt-4">
          <Search className="mt-1 h-5 w-5 shrink-0 text-faint" />
          <textarea
            ref={textareaRef}
            value={query}
            rows={1}
            placeholder="Ask anything — get a grounded, cited answer…"
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
            className="scroll-slim max-h-[220px] w-full resize-none bg-transparent text-[17px] leading-relaxed text-ink outline-none placeholder:text-faint"
          />
        </div>

        <div className="flex items-center justify-between gap-2 px-3 pb-3 pt-2">
          <div className="flex flex-wrap items-center gap-2">
            <ModeSelector value={mode} onChange={setMode} />
            <PersonaSelector value={persona} onChange={setPersona} />
          </div>
          <div className="flex items-center gap-2">
            <kbd className="hidden select-none items-center gap-1 rounded border border-line px-1.5 py-0.5 text-[10px] text-faint sm:inline-flex">
              Enter
            </kbd>
            <button
              type="button"
              onClick={submit}
              disabled={!canSubmit}
              aria-label="Search"
              className={cn(
                'flex h-9 w-9 items-center justify-center rounded-xl transition-all',
                canSubmit
                  ? 'bg-accent text-white hover:bg-accent/90'
                  : 'bg-ink/8 text-faint',
              )}
            >
              <ArrowUp className="h-[18px] w-[18px]" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
