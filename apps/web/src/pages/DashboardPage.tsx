import { useQuery } from '@tanstack/react-query';
import { getDashboard, getSyncRuns } from '../api/client';
import { ArticleCard } from '../components/ArticleCard';
import { EmptyState, ErrorState, LoadingState } from '../components/States';
import { StatCard } from '../components/StatCard';
import { TrendChart } from '../components/TrendChart';
import { formatDateTime } from '../lib/utils';

export function DashboardPage() {
  const dashboardQuery = useQuery({ queryKey: ['dashboard'], queryFn: getDashboard });
  const syncRunsQuery = useQuery({ queryKey: ['sync-runs-summary'], queryFn: getSyncRuns });

  if (dashboardQuery.isLoading) return <LoadingState label="Preparing dashboard…" />;
  if (dashboardQuery.isError || !dashboardQuery.data) {
    return <ErrorState label="Dashboard data could not be loaded." />;
  }

  const latestRun = syncRunsQuery.data?.[0];
  const data = dashboardQuery.data;

  return (
    <div className="page-stack">
      <section className="hero-panel">
        <div>
          <p className="eyebrow">Research operations</p>
          <h2>Track newly published and online-first papers without scraping full article pages.</h2>
        </div>
        <div className="hero-meta">
          <span className="mode-pill">Status: {data.last_sync_status ?? 'unknown'}</span>
          {latestRun?.finished_at ? <span>Last completed {formatDateTime(latestRun.finished_at)}</span> : null}
        </div>
      </section>

      <section className="stats-grid">
        <StatCard label="New today" value={data.today_new_articles} detail="Articles first seen in the last 24h." />
        <StatCard
          label="Tracked journals"
          value={data.by_journal.length}
          detail="Configured sources with RSS-first or Crossref-backed polling."
        />
        <StatCard
          label="Recent sync scope"
          value={latestRun?.scope ?? 'N/A'}
          detail={latestRun ? `${latestRun.total_processed} category jobs finished` : 'No sync history yet.'}
        />
      </section>

      <TrendChart points={data.trend} />

      <section className="split-section">
        <div className="panel">
          <div className="section-header">
            <div>
              <p className="eyebrow">By journal</p>
              <h2>Coverage snapshot</h2>
            </div>
          </div>
          <div className="journal-counts">
            {data.by_journal.map((item) => (
              <div key={item.journal_slug} className="journal-count-row">
                <span>{item.journal_name}</span>
                <strong>{item.count}</strong>
              </div>
            ))}
          </div>
        </div>

        <div className="panel">
          <div className="section-header">
            <div>
              <p className="eyebrow">Latest intake</p>
              <h2>Newest articles</h2>
            </div>
          </div>
          <div className="list-stack">
            {data.latest_articles.length ? (
              data.latest_articles.map((article) => <ArticleCard key={article.id} article={article} />)
            ) : (
              <EmptyState label="No articles synced yet." hint="Run the first sync or wait for the daily schedule." />
            )}
          </div>
        </div>
      </section>
    </div>
  );
}

