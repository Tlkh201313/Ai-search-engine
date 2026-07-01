'use client';

import { Children, isValidElement, type ReactNode } from 'react';
import ReactMarkdown, { type Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';

import type { Source } from '@/lib/types';

import { CitationChip } from './CitationChip';

const CITE_RE = /(\[\d+\])/g;

interface Props {
  content: string;
  sources: Source[];
  onCite: (id: number) => void;
}

export function Markdown({ content, sources, onCite }: Props) {
  const byId = new Map(sources.map((s) => [s.id, s]));

  const withCitations = (children: ReactNode): ReactNode =>
    Children.map(children, (child) => {
      if (typeof child === 'string') {
        const parts = child.split(CITE_RE);
        return parts.map((part, i) => {
          const match = /^\[(\d+)\]$/.exec(part);
          if (match) {
            const id = Number(match[1]);
            return (
              <CitationChip key={i} id={id} source={byId.get(id)} onClick={() => onCite(id)} />
            );
          }
          return part;
        });
      }
      if (isValidElement(child) && child.props?.children) {
        return child;
      }
      return child;
    });

  const components: Components = {
    p: ({ children }) => <p>{withCitations(children)}</p>,
    li: ({ children }) => <li>{withCitations(children)}</li>,
    td: ({ children }) => <td>{withCitations(children)}</td>,
    a: ({ href, children }) => (
      <a href={href} target="_blank" rel="noopener noreferrer">
        {children}
      </a>
    ),
  };

  return (
    <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
      {content}
    </ReactMarkdown>
  );
}
