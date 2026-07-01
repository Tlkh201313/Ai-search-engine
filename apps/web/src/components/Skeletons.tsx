export function SourceCardSkeleton() {
  return (
    <div className="rounded-xl border border-line bg-surface p-3.5">
      <div className="flex items-center gap-2">
        <div className="skeleton h-5 w-5 rounded-md" />
        <div className="skeleton h-3 w-24 rounded" />
      </div>
      <div className="skeleton mt-2.5 h-3.5 w-full rounded" />
      <div className="skeleton mt-1.5 h-3 w-2/3 rounded" />
    </div>
  );
}

export function AnswerSkeleton() {
  return (
    <div className="space-y-3">
      <div className="skeleton h-4 w-3/4 rounded" />
      <div className="skeleton h-4 w-full rounded" />
      <div className="skeleton h-4 w-full rounded" />
      <div className="skeleton h-4 w-5/6 rounded" />
    </div>
  );
}
