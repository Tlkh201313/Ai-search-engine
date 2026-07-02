import Link from 'next/link';

import { cn } from '@/lib/utils';

export function Logo({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 32 32"
      fill="none"
      className={cn('h-7 w-7', className)}
      aria-hidden="true"
    >
      <circle cx="16" cy="16" r="14" stroke="rgb(var(--accent))" strokeWidth="1.6" opacity="0.35" />
      <path
        d="M16 4a12 12 0 0 1 0 24"
        stroke="rgb(var(--accent))"
        strokeWidth="2.2"
        strokeLinecap="round"
      />
      <circle cx="16" cy="16" r="4.4" fill="rgb(var(--accent))" />
      <circle cx="16" cy="16" r="1.6" fill="rgb(var(--surface))" />
    </svg>
  );
}

export function Brand({ className }: { className?: string }) {
  return (
    <Link href="/" className={cn('group inline-flex items-center gap-2.5', className)}>
      <Logo />
      <span className="text-[17px] font-semibold tracking-tight text-ink">
        Lumen
      </span>
    </Link>
  );
}
