// Mirrors the FastAPI backend schemas (apps/api/app/models.py).

export type ResearchMode =
  | 'quick'
  | 'deep'
  | 'compare'
  | 'news'
  | 'academic'
  | 'code';

export type ProgressStage =
  | 'understanding'
  | 'searching'
  | 'finding_sources'
  | 'reading'
  | 'deduping'
  | 'ranking'
  | 'writing'
  | 'verifying'
  | 'done'
  | 'error';

export interface SourceScores {
  relevance: number;
  freshness: number;
  quality: number;
  depth: number;
  overall: number;
}

export interface Source {
  id: number;
  url: string;
  title: string;
  domain: string;
  snippet: string;
  excerpt: string;
  author: string | null;
  description: string | null;
  published_at: string | null;
  fetched_at: string | null;
  favicon: string | null;
  provider: string;
  word_count: number;
  scores: SourceScores;
  used: boolean;
}

export interface Answer {
  summary: string;
  detail: string;
  key_takeaways: string[];
  agreements: string[];
  disagreements: string[];
  uncertainties: string[];
  follow_ups: string[];
  citations: number[];
  confidence: number;
}

export interface ModelInfo {
  model: string;
  available: boolean;
  grounded: boolean;
}

export interface ResearchTimings {
  search_ms: number;
  fetch_ms: number;
  answer_ms: number;
  total_ms: number;
}

export interface ResearchResult {
  id: string;
  query: string;
  mode: ResearchMode;
  status: 'running' | 'complete' | 'error';
  answer: Answer;
  sources: Source[];
  confidence: number;
  model: ModelInfo;
  timings: ResearchTimings;
  error: string | null;
  created_at: string;
}

export interface ProgressEvent {
  stage: ProgressStage;
  status: 'active' | 'done' | 'error';
  message: string;
  progress: number;
  data: {
    delta?: string;
    result?: ResearchResult;
    sources?: Source[];
    subqueries?: string[];
    candidates?: number;
    readable?: number;
    reading?: number;
    used?: number[];
    heartbeat?: boolean;
    cached?: boolean;
    [key: string]: unknown;
  };
}

export interface AppSettings {
  llm_available: boolean;
  model: string;
  grounded: boolean;
  search_providers: string[];
  modes: string[];
}
