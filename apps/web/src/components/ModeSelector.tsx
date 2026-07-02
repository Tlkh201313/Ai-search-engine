'use client';

import { Check, ChevronDown } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';

import { MODE_MAP, MODES } from '@/lib/modes';
import type { ResearchMode } from '@/lib/types';
import { cn } from '@/lib/utils';

interface Props {
  value: ResearchMode;
  onChange: (mode: ResearchMode) => void;
  align?: 'left' | 'right';
  direction?: 'down' | 'up';
}

export function ModeSelector({ value, onChange, align = 'left', direction = 'down' }: Props) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const current = MODE_MAP[value];
  const Icon = current.icon;

  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false);
    document.addEventListener('mousedown', onClick);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onClick);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="chip !py-1.5 !text-[13px]"
        aria-haspopup="listbox"
        aria-expanded={open}
      >
        <Icon className="h-3.5 w-3.5 text-accent" />
        <span className="text-ink">{current.short}</span>
        <ChevronDown className={cn('h-3.5 w-3.5 transition-transform', open && 'rotate-180')} />
      </button>

      {open && (
        <div
          role="listbox"
          className={cn(
            'absolute z-30 w-72 animate-fade-in-fast rounded-xl border border-line bg-raised p-1.5 shadow-float',
            align === 'right' ? 'right-0' : 'left-0',
            direction === 'up' ? 'bottom-full mb-2' : 'top-full mt-2',
          )}
        >
          {MODES.map((m) => {
            const MIcon = m.icon;
            const active = m.key === value;
            return (
              <button
                key={m.key}
                type="button"
                role="option"
                aria-selected={active}
                onClick={() => {
                  onChange(m.key);
                  setOpen(false);
                }}
                className={cn(
                  'flex w-full items-start gap-3 rounded-lg px-2.5 py-2 text-left transition-colors',
                  active ? 'bg-accent/10' : 'hover:bg-ink/5',
                )}
              >
                <MIcon className={cn('mt-0.5 h-4 w-4 shrink-0', active ? 'text-accent' : 'text-faint')} />
                <span className="min-w-0 flex-1">
                  <span className="flex items-center gap-2 text-sm font-medium text-ink">
                    {m.label}
                    {active && <Check className="h-3.5 w-3.5 text-accent" />}
                  </span>
                  <span className="mt-0.5 block text-xs leading-snug text-muted">
                    {m.description}
                  </span>
                </span>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
