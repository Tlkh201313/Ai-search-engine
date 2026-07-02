'use client';

import { useEffect, useState } from 'react';

// Rotating status words, Claude-style. Swap this array to change language.
const WORDS = ['Thinking…', 'Reasoning…', 'Composing…', 'Almost there…'];

export function ThinkingIndicator() {
  const [i, setI] = useState(0);

  useEffect(() => {
    const t = setInterval(() => setI((n) => (n + 1) % WORDS.length), 1800);
    return () => clearInterval(t);
  }, []);

  return (
    <div className="flex items-center gap-2.5 py-1 text-[15px] text-muted animate-fade-in">
      <span className="flex gap-1">
        <span className="h-1.5 w-1.5 rounded-full bg-accent animate-pulse-dot" />
        <span
          className="h-1.5 w-1.5 rounded-full bg-accent animate-pulse-dot"
          style={{ animationDelay: '0.2s' }}
        />
        <span
          className="h-1.5 w-1.5 rounded-full bg-accent animate-pulse-dot"
          style={{ animationDelay: '0.4s' }}
        />
      </span>
      <span key={i} className="thinking-shimmer animate-fade-in-fast font-medium">
        {WORDS[i]}
      </span>
    </div>
  );
}
