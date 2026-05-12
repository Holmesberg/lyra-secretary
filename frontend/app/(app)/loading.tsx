export default function AppRouteLoading() {
  return (
    <div className="space-y-6">
      <div className="h-8 w-44 animate-pulse rounded-sm bg-void-2/80" />
      <div className="grid gap-4 lg:grid-cols-2">
        {[0, 1, 2, 3].map((i) => (
          <div
            key={i}
            className="h-28 animate-pulse rounded-sm border border-hairline bg-void-2/60"
          />
        ))}
      </div>
      <div className="h-48 animate-pulse rounded-sm border border-hairline bg-void-2/40" />
    </div>
  );
}
