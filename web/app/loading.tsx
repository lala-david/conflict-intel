export default function Loading() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background">
      <div className="flex flex-col items-center gap-4">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-border border-t-accent" />
        <span className="text-sm text-text-dim">Loading…</span>
      </div>
    </div>
  );
}
