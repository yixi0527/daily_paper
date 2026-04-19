import { formatDateTime } from '../lib/utils';
import { useQuery } from '@tanstack/react-query';
import { getJournals } from '../api/client';
import { EmptyState, ErrorState, LoadingState } from '../components/States';

export function JournalsPage() {
  const journalsQuery = useQuery({ queryKey: ['journals'], queryFn: getJournals });

  if (journalsQuery.isLoading) return <LoadingState label="Loading journal configuration…" />;
  if (journalsQuery.isError || !journalsQuery.data) return <ErrorState label="Journal configuration could not be loaded." />;

  return (
    <div className="page-stack">
      <section className="page-header">
        <div>
          <p className="eyebrow">Sources</p>
          <h2>Configured journals</h2>
        </div>
        <p className="muted">Each journal is driven by a dedicated adapter with RSS-first fallback strategy.</p>
      </section>

      <section className="panel">
        <div className="list-stack">
          {journalsQuery.data.length ? (
            journalsQuery.data.map((journal) => (
              <article className="journal-panel" key={journal.slug}>
                <div>
                  <p className="eyebrow">{journal.publisher}</p>
                  <h3>{journal.journal_name}</h3>
                  <p className="muted">
                    Strategy: {journal.polling_strategy} · Primary {journal.primary_source ?? 'n/a'} · Fallback{' '}
                    {journal.fallback_source ?? 'n/a'}
                  </p>
                  {journal.source_states?.length ? (
                    <div className="article-footer">
                      {journal.source_states.map((state) => (
                        <span className="pill" key={`${journal.slug}-${state.source_category}`}>
                          {state.source_category}: {state.last_success_at ? formatDateTime(state.last_success_at) : 'never'}
                        </span>
                      ))}
                    </div>
                  ) : null}
                </div>
                <a href={journal.homepage_url} target="_blank" rel="noreferrer" className="ghost-button">
                  Open journal
                </a>
              </article>
            ))
          ) : (
            <EmptyState label="No journals have been seeded yet." />
          )}
        </div>
      </section>
    </div>
  );
}
