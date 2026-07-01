'use client';

import {
  ArrowRight,
  CircleAlert,
  GitCompareArrows,
  Sparkles,
} from 'lucide-react';

import type { ResearchState } from '@/hooks/useResearch';
import type { ResearchMode } from '@/lib/types';
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

export function AnswerView({ state, onCite, onFollowUp, mode }: Props) {
  const { result, sources, answerText, status } = state;
  const answer = result?.answer;
  const streaming = status === 'running';

  const conf = confidenceLabel(result?.confidence ?? 0);

  return (
    <div className="animate-fade-in">
      {/* Direct answer */}
      {answer?.summary && (
        <div className="mb-5 border-l-2 border-accent/50 pl-4">
          <p className="font-serif text-lg leading-relaxed text-ink">{answer.summary}</p>
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

          {/* Meta footer */}
          {result && (
            <div className="mt-6 flex flex-wrap items-center gap-x-3 gap-y-1 border-t border-line pt-4 text-xs text-faint">
              <span className={cn('font-medium', conf.tone)}>{conf.label}</span>
              <span>·</span>
              <span>{sources.length} sources</span>
              {result.timings.total_ms > 0 && (
                <>
                  <span>·</span>
                  <span>{formatMs(result.timings.total_ms)}</span>
                </>
              )}
              <span>·</span>
              <span>
                {result.model.grounded ? result.model.model : 'extractive mode'}
              </span>
            </div>
          )}

          {answer.follow_ups.length > 0 && (
            <section className="mt-6">
              <SectionTitle icon={ArrowRight}>Follow-up questions</SectionTitle>
              <div className="mt-3 flex flex-col gap-2">
                {answer.follow_ups.map((q, i) => (
                  <button
                    key={i}
                    type="button"
                    onClick={() => onFollowUp(q, mode)}
                    className="group flex items-center justify-between gap-3 rounded-lg border border-line bg-surface px-3.5 py-2.5 text-left text-sm text-ink transition-colors hover:border-accent/40 hover:bg-accent/[0.04]"
                  >
                    <span>{q}</span>
                    <ArrowRight className="h-4 w-4 shrink-0 text-faint transition-transform group-hover:translate-x-0.5 group-hover:text-accent" />
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
