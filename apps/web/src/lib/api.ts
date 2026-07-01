import type {
  AppSettings,
  ProgressEvent,
  ResearchMode,
  ResearchResult,
} from './types';

export const API_BASE = (
  process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'
).replace(/\/$/, '');

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body?.detail ?? detail;
    } catch {
      /* ignore */
    }
    throw new ApiError(detail, res.status);
  }
  return res.json() as Promise<T>;
}

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

export interface ConversationTurn {
  query: string;
  answer: string;
}

export async function createResearch(
  query: string,
  mode: ResearchMode,
  context: ConversationTurn[] = [],
): Promise<{ id: string; query: string; mode: ResearchMode }> {
  const res = await fetch(`${API_BASE}/api/research`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ query, mode, context }),
  });
  return json(res);
}

export async function getResearch(id: string): Promise<ResearchResult> {
  return json(await fetch(`${API_BASE}/api/research/${id}`));
}

export async function getSettings(): Promise<AppSettings> {
  return json(await fetch(`${API_BASE}/api/settings`));
}

export interface StreamHandlers {
  onEvent: (event: ProgressEvent) => void;
  onError?: (err: Error) => void;
}

/** Open an SSE stream for a research session. Returns a close() function. */
export function openResearchStream(id: string, handlers: StreamHandlers): () => void {
  const source = new EventSource(`${API_BASE}/api/research/${id}/stream`);
  let closed = false;

  source.onmessage = (msg) => {
    try {
      const event = JSON.parse(msg.data) as ProgressEvent;
      handlers.onEvent(event);
      if (event.stage === 'done' || event.stage === 'error') {
        closed = true;
        source.close();
      }
    } catch {
      /* ignore malformed frames */
    }
  };

  source.onerror = () => {
    if (closed) return;
    // EventSource auto-retries; surface a soft error and stop after failure.
    source.close();
    handlers.onError?.(new Error('Connection to the research stream was lost.'));
  };

  return () => {
    closed = true;
    source.close();
  };
}
