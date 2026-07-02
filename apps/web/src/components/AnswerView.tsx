'use client';

import {
  Check,
  CircleAlert,
  Copy,
  Download,
  GitCompareArrows,
  Link2,
  Plus,
  RotateCw,
  Sparkles,
  ThumbsDown,
  ThumbsUp,
} from 'lucide-react';
import { useState } from 'react';

import type { ResearchState } from '@/hooks/useResearch';
import type { Answer, ResearchMode, Source } from '@/lib/types';
import { cn, confidenceLabel, formatMs } from '@/lib/utils';

import { AnswerSkeleton } from './Skeletons';
import { Markdown } from './Markdown';

interface Props {
  state: ResearchState;
  onCite: (id: number) => void;
  onFollowUp: (query: string, mode: ResearchMode) => void;
  mode: ResearchMode;
}

function SectionTitle({ icon: Icon, children }: { icon?: React.ElementType; children: React.ReactNode }) {
  return (
    <h3 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-faint">
      {Icon && <Icon className="h-3.5 w-3.5" />}
      {children}
    </h3>
  );
}

function answerToText(answer: Answer, sources: Source[]): string {
  const lines: string[] = [];
  if (answer.summary) lines.push(answer.summary, '');
  if (answer.detail) lines.push(answer.detail, '');
  if (answer.key_takeaways.length) {
    lines.push('Key takeaways:');
    answer.key_takeaways.forEach((t) => lines.push(`- ${t}`));
    lines.push('');
  }
  if (sources.length) {
    lines.push('Sources:');
    sources.forEach((s) => lines.push(`[${s.id}] ${s.title} — ${s.url}`));
  }
  return lines.join('\n').trim();
}

function IconAction({
  label,
  icon: Icon,
  onClick,
  active = false,
}: {
  label: string;
  icon: React.ElementType;
  onClick: () => void;
  active?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      title={label}
      aria-label={label}
      className={cn(
        'flex h-8 w-8 items-center justify-center rounded-lg transition-all hover:bg-ink/5 active:scale-90',
        active ? 'text-accent' : 'text-faint hover:text-ink',
      )}
    >
      <Icon className="h-4 w-4" />
    </button>
  );
}

function CopyAction({ label, icon, getText }: { label: string; icon: React.ElementType; getText: () => string }) {
  const [done, setDone] = useState(false);
  return (
    <IconAction
      label={done ? 'Copied' : label}
      icon={done ? Check : icon}
      active={done}
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(getText());
          setDone(true);
          setTimeout(() => setDone(false), 1600);
        } catch {
          /* clipboard unavailable */
        }
      }}
    />
  );
}

function downloadMarkdown(filename: string, text: string) {
  const blob = new Blob([text], { type: 'text/markdown' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function useFeedback(id: string): ['up' | 'down' | null, (v: 'up' | 'down') => void] {
  const [fb, setFb] = useState<'up' | 'down' | null>(() => {
    if (typeof window === 'undefined') return null;
    try {
      return localStorage.getItem(`are:fb:${id}`) as 'up' | 'down' | null;
    } catch {
      return null;
    }
  });
  const vote = (v: 'up' | 'down') => {
    const next = fb === v ? null : v;
    setFb(next);
    try {
      if (next) localStorage.setItem(`are:fb:${id}`, next);
      else localStorage.removeItem(`are:fb:${id}`);
    } catch {
      /* ignore */
    }
  };
  return [fb, vote];
}

export function AnswerView({ state, onCite, onFollowUp, mode }: Props) {
  const { result, sources, answerText, status } = state;
  const answer = result?.answer;
  const streaming = status === 'running';
  const [fb, vote] = useFeedback(result?.id ?? '');

  const conf = confidenceLabel(result?.confidence ?? 0);

  return (
    <div className="animate-fade-in">

      {/* Direct answer */}
      {answer?.summary && (
        <div className="mb-5 border-l-2 border-accent/50 pl-4">
          <p className="text-lg leading-relaxed text-ink">{answer.summary}</p>
        </div>
      )}

      {/* Detail (streams live, then settles to the final markdown) */}
      <div className="answer-prose">
        {answerText ? (
          <>
            <Markdown content={answerText} sources={sources} onCite={onCite} />
            {streaming && (
              <span className="ml-0.5 inline-block h-[1.1em] w-[2px] translate-y-[2px] animate-blink bg-accent align-middle" />
            )}
          </>
        ) : (
          <AnswerSkeleton />
        )}
      </div>

      {answer && (
        <>
          {answer.key_takeaways.length > 0 && (
            <section className="mt-7">
              <SectionTitle icon={Sparkles}>Key takeaways</SectionTitle>
              <ul className="mt-3 space-y-2">
                {answer.key_takeaways.map((t, i) => (
                  <li key={i} className="flex gap-2.5 text-[15px] leading-relaxed text-ink">
                    <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-accent/60" />
                    <span>
                      <Markdown content={t} sources={sources} onCite={onCite} />
                    </span>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {(answer.agreements.length > 0 || answer.disagreements.length > 0) && (
            <section className="mt-7 grid gap-4 sm:grid-cols-2">
              {answer.agreements.length > 0 && (
                <div className="rounded-xl border border-line bg-surface p-4">
                  <SectionTitle icon={GitCompareArrows}>Sources agree</SectionTitle>
                  <ul className="mt-2.5 space-y-2 text-sm leading-relaxed text-muted">
                    {answer.agreements.map((t, i) => (
                      <li key={i}>
                        <Markdown content={t} sources={sources} onCite={onCite} />
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {answer.disagreements.length > 0 && (
                <div className="rounded-xl border border-line bg-surface p-4">
                  <SectionTitle icon={GitCompareArrows}>Sources disagree</SectionTitle>
                  <ul className="mt-2.5 space-y-2 text-sm leading-relaxed text-muted">
                    {answer.disagreements.map((t, i) => (
                      <li key={i}>
                        <Markdown content={t} sources={sources} onCite={onCite} />
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </section>
          )}

          {answer.uncertainties.length > 0 && (
            <section className="mt-6 rounded-xl border border-amber-500/25 bg-amber-500/5 p-4">
              <SectionTitle icon={CircleAlert}>Uncertainties &amp; gaps</SectionTitle>
              <ul className="mt-2.5 space-y-1.5 text-sm leading-relaxed text-muted">
                {answer.uncertainties.map((t, i) => (
                  <li key={i} className="flex gap-2">
                    <span className="text-amber-500">•</span>
                    <span>{t}</span>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {/* Action bar + meta */}
          {result && (
            <div className="mt-5 flex flex-wrap items-center justify-between gap-2 border-t border-line pt-2.5">
              <div className="flex items-center gap-0.5">
                <CopyAction
                  label="Copy link"
                  icon={Link2}
                  getText={() => (typeof window !== 'undefined' ? window.location.href : '')}
                />
                <IconAction
                  label="Export markdown"
                  icon={Download}
                  onClick={() =>
                    downloadMarkdown(
                      `lumen-${result.id}.md`,
                      `# ${result.query}\n\n${answerToText(answer, sources)}`,
                    )
                  }
                />
                <CopyAction label="Copy answer" icon={Copy} getText={() => answerToText(answer, sources)} />
                <IconAction label="Rewrite" icon={RotateCw} onClick={() => onFollowUp(result.query, mode)} />
                <span className="mx-1.5 h-4 w-px bg-line" />
                <IconAction
                  label="Good answer"
                  icon={ThumbsUp}
                  active={fb === 'up'}
                  onClick={() => vote('up')}
                />
                <IconAction
                  label="Not helpful"
                  icon={ThumbsDown}
                  active={fb === 'down'}
                  onClick={() => vote('down')}
                />
              </div>
              <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-faint">
                <span className={cn('font-medium', conf.tone)}>{conf.label}</span>
                {sources.length > 0 && (
                  <>
                    <span>·</span>
                    <span>{sources.length} sources</span>
                  </>
                )}
                {result.timings.total_ms > 0 && (
                  <>
                    <span>·</span>
                    <span>{formatMs(result.timings.total_ms)}</span>
                  </>
                )}
                <span>·</span>
                <span>{result.model.grounded ? result.model.model : 'extractive mode'}</span>
              </div>
            </div>
          )}

          {answer.follow_ups.length > 0 && (
            <section className="mt-6">
              <SectionTitle icon={Sparkles}>Related</SectionTitle>
              <div className="mt-2 flex flex-col divide-y divide-line">
                {answer.follow_ups.map((q, i) => (
                  <button
                    key={i}
                    type="button"
                    onClick={() => onFollowUp(q, mode)}
                    style={{ animationDelay: `${i * 70}ms` }}
                    className="group flex items-center justify-between gap-3 py-3 text-left text-[15px] font-medium text-ink transition-colors animate-slide-up hover:text-accent"
                  >
                    <span>{q}</span>
                    <Plus className="h-4 w-4 shrink-0 text-faint transition-colors group-hover:text-accent" />
                  </button>
                ))}
              </div>
            </section>
          )}
        </>
      )}
    </div>
  );
}
