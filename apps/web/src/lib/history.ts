import type { ResearchMode } from './types';

const RECENT_KEY = 'are:recent';
const PENDING_KEY = 'are:pending';
const MAX_RECENT = 12;

export interface RecentSearch {
  id: string;
  query: string;
  mode: ResearchMode;
  ts: number;
}

export function getRecent(): RecentSearch[] {
  if (typeof window === 'undefined') return [];
  try {
    return JSON.parse(localStorage.getItem(RECENT_KEY) ?? '[]');
  } catch {
    return [];
  }
}

export function addRecent(entry: RecentSearch): void {
  if (typeof window === 'undefined') return;
  const existing = getRecent().filter(
    (e) => e.query.trim().toLowerCase() !== entry.query.trim().toLowerCase(),
  );
  const next = [entry, ...existing].slice(0, MAX_RECENT);
  localStorage.setItem(RECENT_KEY, JSON.stringify(next));
}

export function clearRecent(): void {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(RECENT_KEY);
}

/** Hand off a freshly created research so the target page knows to stream it. */
export interface PendingResearch {
  query: string;
  mode: ResearchMode;
}

export function setPending(id: string, pending: PendingResearch): void {
  if (typeof window === 'undefined') return;
  sessionStorage.setItem(`${PENDING_KEY}:${id}`, JSON.stringify(pending));
}

export function takePending(id: string): PendingResearch | null {
  if (typeof window === 'undefined') return null;
  const key = `${PENDING_KEY}:${id}`;
  const raw = sessionStorage.getItem(key);
  if (!raw) return null;
  sessionStorage.removeItem(key);
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}
