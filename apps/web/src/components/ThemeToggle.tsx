'use client';

import { Monitor, Moon, Sun } from 'lucide-react';
import { useTheme } from 'next-themes';
import { useEffect, useState } from 'react';

import { cn } from '@/lib/utils';

const OPTIONS = [
  { value: 'light', icon: Sun, label: 'Light' },
  { value: 'system', icon: Monitor, label: 'System' },
  { value: 'dark', icon: Moon, label: 'Dark' },
] as const;

export function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  if (!mounted) {
    return <div className="h-8 w-[104px] rounded-full border border-line" />;
  }

  return (
    <div className="inline-flex items-center gap-0.5 rounded-full border border-line bg-surface p-0.5">
      {OPTIONS.map(({ value, icon: Icon, label }) => (
        <button
          key={value}
          type="button"
          onClick={() => setTheme(value)}
          aria-label={`${label} theme`}
          title={`${label} theme`}
          className={cn(
            'flex h-7 w-7 items-center justify-center rounded-full transition-colors',
            theme === value
              ? 'bg-accent/12 text-accent'
              : 'text-faint hover:text-ink',
          )}
        >
          <Icon className="h-4 w-4" />
        </button>
      ))}
    </div>
  );
}
