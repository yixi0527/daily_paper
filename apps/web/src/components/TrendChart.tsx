export function TrendChart({ points }: { points: Array<{ date: string; count: number }> }) {
  if (!points.length) return null;
  const maxValue = Math.max(...points.map((point) => point.count), 1);
  const coordinates = points
    .map((point, index) => {
      const x = (index / Math.max(points.length - 1, 1)) * 100;
      const y = 100 - (point.count / maxValue) * 100;
      return `${x},${y}`;
    })
    .join(' ');

  return (
    <section className="chart-panel">
      <div className="section-header">
        <div>
          <p className="eyebrow">Last 7 days</p>
          <h2>Ingestion trend</h2>
        </div>
      </div>
      <svg viewBox="0 0 100 100" className="trend-chart" preserveAspectRatio="none">
        <polyline points={coordinates} />
      </svg>
      <div className="trend-labels">
        {points.map((point) => (
          <div key={point.date}>
            <strong>{point.count}</strong>
            <span>{point.date.slice(5)}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

