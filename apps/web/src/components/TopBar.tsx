'use client';

import { Plus } from 'lucide-react';
import Link from 'next/link';

import { Brand } from './Brand';
import { ThemeToggle } from './ThemeToggle';

export function TopBar({ showNew = true }: { showNew?: boolean }) {
  return (
    <header className="sticky top-0 z-20 border-b border-line/70 bg-paper/80 backdrop-blur-md">
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4 sm:px-6">
        <Brand />
        <div className="flex items-center gap-2">
          {showNew && (
            <Link href="/" className="btn-ghost hidden sm:inline-flex">
              <Plus className="h-4 w-4" />
              New search
            </Link>
          )}
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}
