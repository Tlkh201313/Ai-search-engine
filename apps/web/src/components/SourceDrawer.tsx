'use client';

import { X } from 'lucide-react';
import { useEffect } from 'react';

import type { Source } from '@/lib/types';

import { SourcePanel } from './SourcePanel';

interface Props {
  open: boolean;
  onClose: () => void;
  sources: Source[];
  highlightId?: number | null;
}

export function SourceDrawer({ open, onClose, sources, highlightId }: Props) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    if (open) document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-40 lg:hidden">
      <div
        className="absolute inset-0 bg-black/40 animate-fade-in-fast"
        onClick={onClose}
        aria-hidden="true"
      />
      <div className="absolute inset-x-0 bottom-0 max-h-[78dvh] overflow-hidden rounded-t-2xl border-t border-line bg-paper shadow-float animate-fade-in">
        <div className="flex items-center justify-between border-b border-line px-4 py-3">
          <span className="text-sm font-medium text-ink">
            Sources <span className="text-muted">({sources.length})</span>
          </span>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close sources"
            className="btn-ghost !p-1.5"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="scroll-slim max-h-[calc(78dvh-3.25rem)] overflow-y-auto p-4">
          <SourcePanel sources={sources} highlightId={highlightId} anchorPrefix="draw" />
        </div>
      </div>
    </div>
  );
}
