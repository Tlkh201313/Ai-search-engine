'use client';

import { Sparkles } from 'lucide-react';

import type { NewsItem } from '@/lib/news';
import { faviconFor, relativeTime } from '@/lib/utils';

interface Props {
  item: NewsItem;
  onAsk: (title: string) => void;
  asking?: boolean;
  hero?: boolean;
}

function SourceLine({ item }: { item: NewsItem }) {
  const time = relativeTime(item.published_at);
  return (
    <span className="flex items-center gap-1.5 text-xs text-muted">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={faviconFor(item.domain)} alt="" className="h-3.5 w-3.5 rounded-sm" />
      <span className="font-medium">{item.source}</span>
      {time && <span className="text-faint">· {time}</span>}
    </span>
  );
}

function AskButton({
  title,
  onAsk,
  asking,
  light,
}: Pick<Props, 'onAsk' | 'asking'> & { title: string; light?: boolean }) {
  return (
    <button
      type="button"
      disabled={asking}
      onClick={(e) => {
        e.preventDefault();
        e.stopPropagation();
        onAsk(title);
      }}
      className={`relative z-20 inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium transition-colors disabled:opacity-50 ${
        light
          ? 'bg-white/15 text-white backdrop-blur hover:bg-white/25'
          : 'bg-accent-soft text-accent hover:bg-accent hover:text-white'
      }`}
    >
      <Sparkles className="h-3.5 w-3.5" />
      Ask Lumen
    </button>
  );
}

/** One story. The whole card opens the article; “Ask Lumen” starts research. */
export function NewsCard({ item, onAsk, asking, hero }: Props) {
  if (hero) {
    return (
      <article className="group relative overflow-hidden rounded-2xl border border-line bg-surface shadow-card transition-transform duration-200 hover:-translate-y-0.5">
        <a
          href={item.url}
          target="_blank"
          rel="noopener noreferrer"
          aria-label={item.title}
          className="absolute inset-0 z-10"
        />
        {item.image && (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={item.image}
            alt=""
            referrerPolicy="no-referrer"
            className="aspect-[16/8] w-full object-cover transition-transform duration-500 group-hover:scale-[1.02]"
          />
        )}
        <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/85 via-black/45 to-transparent p-5 pt-16">
          <span className="flex items-center gap-1.5 text-xs text-white/80">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={faviconFor(item.domain)} alt="" className="h-3.5 w-3.5 rounded-sm" />
            <span className="font-medium">{item.source}</span>
            {relativeTime(item.published_at) && (
              <span className="text-white/60">· {relativeTime(item.published_at)}</span>
            )}
          </span>
          <h2 className="mt-1.5 text-xl font-semibold leading-snug text-white sm:text-2xl">
            {item.title}
          </h2>
          <div className="mt-3">
            <AskButton title={item.title} onAsk={onAsk} asking={asking} light />
          </div>
        </div>
      </article>
    );
  }

  return (
    <article className="group relative flex flex-col overflow-hidden rounded-2xl border border-line bg-surface shadow-subtle transition-all duration-200 hover:-translate-y-0.5 hover:border-accent/30 hover:shadow-card">
      <a
        href={item.url}
        target="_blank"
        rel="noopener noreferrer"
        aria-label={item.title}
        className="absolute inset-0 z-10"
      />
      {item.image && (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={item.image}
          alt=""
          loading="lazy"
          referrerPolicy="no-referrer"
          className="aspect-video w-full object-cover"
        />
      )}
      <div className="flex flex-1 flex-col gap-2 p-4">
        <SourceLine item={item} />
        <h3 className="line-clamp-3 text-[15px] font-semibold leading-snug text-ink transition-colors group-hover:text-accent">
          {item.title}
        </h3>
        {item.summary && !item.image && (
          <p className="line-clamp-3 text-[13px] leading-relaxed text-muted">{item.summary}</p>
        )}
        <div className="mt-auto pt-2">
          <AskButton title={item.title} onAsk={onAsk} asking={asking} />
        </div>
      </div>
    </article>
  );
}
