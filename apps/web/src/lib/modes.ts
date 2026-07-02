import {
  Zap,
  Telescope,
  Scale,
  Newspaper,
  GraduationCap,
  Code2,
  type LucideIcon,
} from 'lucide-react';

import type { ResearchMode } from './types';

export interface ModeMeta {
  key: ResearchMode;
  label: string;
  short: string;
  description: string;
  icon: LucideIcon;
}

export const MODES: ModeMeta[] = [
  {
    key: 'quick',
    label: 'Quick Answer',
    short: 'Quick',
    description: 'A fast, direct answer from a few strong sources.',
    icon: Zap,
  },
  {
    key: 'deep',
    label: 'Deep Research',
    short: 'Deep',
    description: 'Broad search, more sources, thorough synthesis.',
    icon: Telescope,
  },
  {
    key: 'compare',
    label: 'Compare Sources',
    short: 'Compare',
    description: 'Surface where sources agree and disagree.',
    icon: Scale,
  },
  {
    key: 'news',
    label: 'Latest News',
    short: 'News',
    description: 'Prioritize the most recent, timely reporting.',
    icon: Newspaper,
  },
  {
    key: 'academic',
    label: 'Academic',
    short: 'Academic',
    description: 'Favor papers, references, and authoritative work.',
    icon: GraduationCap,
  },
  {
    key: 'code',
    label: 'Code / Technical',
    short: 'Code',
    description: 'Favor docs, GitHub, and technical Q&A.',
    icon: Code2,
  },
];

export const MODE_MAP: Record<ResearchMode, ModeMeta> = MODES.reduce(
  (acc, m) => ({ ...acc, [m.key]: m }),
  {} as Record<ResearchMode, ModeMeta>,
);

export const STAGE_LABELS: Record<string, string> = {
  understanding: 'Understanding your question',
  searching: 'Searching the web',
  finding_sources: 'Finding sources',
  reading: 'Reading pages',
  deduping: 'Removing duplicates',
  ranking: 'Ranking evidence',
  writing: 'Writing the answer',
  verifying: 'Checking citations',
  done: 'Done',
  error: 'Error',
};

export const STAGE_ORDER: string[] = [
  'understanding',
  'searching',
  'finding_sources',
  'reading',
  'deduping',
  'ranking',
  'writing',
  'verifying',
];

export const EXAMPLE_PROMPTS: { q: string; mode: ResearchMode }[] = [
  { q: 'How does mRNA vaccine technology actually work?', mode: 'deep' },
  { q: 'What are the latest developments in fusion energy?', mode: 'news' },
  { q: 'Compare Rust and Go for building web backends', mode: 'compare' },
  { q: 'What does recent research say about intermittent fasting?', mode: 'academic' },
  { q: 'How do I implement rate limiting in FastAPI?', mode: 'code' },
  { q: 'What caused the 2008 financial crisis?', mode: 'quick' },
];
