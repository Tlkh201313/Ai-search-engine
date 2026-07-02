import type { ResearchMode, ResearchResult } from './types';

// Local thread archive: completed turns are saved so reopening a thread from
// the Library restores it instantly instead of re-running every query.
const THREAD_KEY = 'are:thread';
const INDEX_KEY = 'are:threads';
const MAX_THREADS = 20;

export interface SavedTurn {
  id: string;
  query: string;
  mode: ResearchMode;
  result: ResearchResult;
}

function slim(result: ResearchResult): ResearchResult {
  // Drop the bulky per-source excerpts — nothing in the UI renders them.
  return {
    ...result,
    sources: result.sources.map((s) => ({ ...s, excerpt: '' })),
  };
}

export function saveThread(threadId: string, turns: SavedTurn[]): void {
  if (typeof window === 'undefined' || turns.length === 0) return;
  try {
    const payload = turns.map((t) => ({ ...t, result: slim(t.result) }));
    localStorage.setItem(`${THREAD_KEY}:${threadId}`, JSON.stringify(payload));
    const index: string[] = JSON.parse(localStorage.getItem(INDEX_KEY) ?? '[]');
    const next = [threadId, ...index.filter((id) => id !== threadId)];
    for (const stale of next.slice(MAX_THREADS)) {
      localStorage.removeItem(`${THREAD_KEY}:${stale}`);
    }
    localStorage.setItem(INDEX_KEY, JSON.stringify(next.slice(0, MAX_THREADS)));
  } catch {
    /* storage full/unavailable — archives are best-effort */
  }
}

export function loadThread(threadId: string): SavedTurn[] | null {
  if (typeof window === 'undefined') return null;
  try {
    const raw = localStorage.getItem(`${THREAD_KEY}:${threadId}`);
    const turns = raw ? (JSON.parse(raw) as SavedTurn[]) : null;
    return turns && turns.length ? turns : null;
  } catch {
    return null;
  }
}
