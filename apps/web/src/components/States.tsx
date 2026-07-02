import { AlertTriangle, Inbox, Loader2 } from 'lucide-react';

export function LoadingState({ label = 'Loading data…' }: { label?: string }) {
  return (
    <div className="state-panel">
      <Loader2 className="state-icon spin" size={22} strokeWidth={2.2} aria-hidden="true" />
      <p>{label}</p>
    </div>
  );
}

export function ErrorState({ label }: { label: string }) {
  return (
    <div className="state-panel error">
      <AlertTriangle className="state-icon" size={24} strokeWidth={2.2} aria-hidden="true" />
      <p>{label}</p>
    </div>
  );
}

export function EmptyState({ label, hint }: { label: string; hint?: string }) {
  return (
    <div className="state-panel empty">
      <Inbox className="state-icon" size={24} strokeWidth={2.2} aria-hidden="true" />
      <p>{label}</p>
      {hint ? <small>{hint}</small> : null}
    </div>
  );
}
