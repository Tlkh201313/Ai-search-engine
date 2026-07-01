'use client';

import { Info, WifiOff } from 'lucide-react';
import { useEffect, useState } from 'react';

import { API_BASE, getSettings } from '@/lib/api';
import type { AppSettings } from '@/lib/types';

export function StatusNotice() {
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [offline, setOffline] = useState(false);

  useEffect(() => {
    getSettings()
      .then(setSettings)
      .catch(() => setOffline(true));
  }, []);

  if (offline) {
    return (
      <div className="flex items-center gap-2 rounded-lg border border-amber-500/30 bg-amber-500/5 px-3.5 py-2.5 text-xs text-muted">
        <WifiOff className="h-4 w-4 shrink-0 text-amber-500" />
        <span>
          Can&apos;t reach the API at <code className="font-mono">{API_BASE}</code>. Start the
          backend, then reload.
        </span>
      </div>
    );
  }

  if (settings && !settings.llm_available) {
    return (
      <div className="flex items-center gap-2 rounded-lg border border-line bg-surface px-3.5 py-2.5 text-xs text-muted">
        <Info className="h-4 w-4 shrink-0 text-faint" />
        <span>
          Running in <strong className="font-medium text-ink">extractive mode</strong> — answers
          are quoted from sources. Configure a model to get fully synthesized answers.
        </span>
      </div>
    );
  }

  return null;
}
