export function LoadingState({ label = 'Loading data…' }: { label?: string }) {
  return (
    <div className="state-panel">
      <div className="pulse-dot" />
      <p>{label}</p>
    </div>
  );
}

export function ErrorState({ label }: { label: string }) {
  return (
    <div className="state-panel error">
      <p>{label}</p>
    </div>
  );
}

export function EmptyState({ label, hint }: { label: string; hint?: string }) {
  return (
    <div className="state-panel empty">
      <p>{label}</p>
      {hint ? <small>{hint}</small> : null}
    </div>
  );
}

