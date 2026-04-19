import { ReactNode } from 'react';

export function StatCard({
  label,
  value,
  detail,
}: {
  label: string;
  value: ReactNode;
  detail?: string;
}) {
  return (
    <section className="stat-card">
      <p className="eyebrow">{label}</p>
      <h3>{value}</h3>
      {detail ? <p className="muted">{detail}</p> : null}
    </section>
  );
}

