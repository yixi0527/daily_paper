import { useQuery } from '@tanstack/react-query';
import { getDashboard, getSyncRuns } from '../api/client';
import { ArticleCard } from '../components/ArticleCard';
import { EmptyState, ErrorState, LoadingState } from '../components/States';
import { formatDateTime } from '../lib/utils';

export function DashboardPage() {
  const dashboardQuery = useQuery({ queryKey: ['dashboard'], queryFn: getDashboard });
  const syncRunsQuery = useQuery({ queryKey: ['sync-runs-summary'], queryFn: getSyncRuns });

  if (dashboardQuery.isLoading) return <LoadingState label="Preparing latest articles…" />;
  if (dashboardQuery.isError || !dashboardQuery.data) {
    return <ErrorState label="Latest articles could not be loaded." />;
  }

  const latestRun = syncRunsQuery.data?.[0];
  const data = dashboardQuery.data;

  return (
    <div className="page-stack">
      <section className="hero-panel hero-panel-compact">
        <div>
          <p className="eyebrow">Latest papers</p>
          <h2>Newest research, review, and perspective articles from the tracked journals.</h2>
        </div>
        <div className="hero-meta">
          <span className="mode-pill">Sync: {data.last_sync_status ?? 'unknown'}</span>
          {latestRun?.finished_at ? (
            <span>Last completed {formatDateTime(latestRun.finished_at)}</span>
          ) : (
            <span>No completed sync yet</span>
          )}
        </div>
      </section>

      <section className="panel">
        <div className="section-header">
          <div>
            <p className="eyebrow">Feed</p>
            <h2>Latest ingested articles</h2>
          </div>
        </div>
        <div className="list-stack">
          {data.latest_articles.length ? (
            data.latest_articles.map((article) => <ArticleCard key={article.id} article={article} />)
          ) : (
            <EmptyState
              label="No articles synced yet."
              hint="Run the first sync or wait for the daily schedule."
            />
          )}
        </div>
      </section>
    </div>
  );
}
