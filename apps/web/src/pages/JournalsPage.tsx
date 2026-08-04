import { formatDateTime } from '../lib/utils';
import { useQuery } from '@tanstack/react-query';
import { ExternalLink } from 'lucide-react';
import { getJournals } from '../api/client';
import { EmptyState, ErrorState, LoadingState } from '../components/States';

export function JournalsPage() {
  const journalsQuery = useQuery({ queryKey: ['journals'], queryFn: getJournals });

  if (journalsQuery.isLoading) return <LoadingState label="Loading journal configuration…" />;
  if (journalsQuery.isError || !journalsQuery.data)
    return <ErrorState label="Journal configuration could not be loaded." />;

  return (
    <div className="page-stack">
      <section className="page-header">
        <div>
          <p className="eyebrow">Sources</p>
          <h2>Configured journals</h2>
        </div>
        <p className="muted">
          Each journal is synchronized from Crossref and indexed by DOI.
        </p>
      </section>

      <section className="panel">
        <div className="list-stack">
          {journalsQuery.data.length ? (
            journalsQuery.data.map((journal) => (
              <article className="journal-panel" key={journal.slug}>
                <div>
                  {(() => {
                    const doiState = journal.source_states?.find(
                      (state) => state.source_category === 'doi',
                    );

                    return (
                      <>
                  <p className="eyebrow">{journal.publisher}</p>
                  <h3>{journal.journal_name}</h3>
                  <p className="muted">Index: DOI</p>
                  {doiState ? (
                    <div className="article-footer">
                      <span className="pill">
                        Last successful DOI sync:{' '}
                        {doiState.last_success_at ? formatDateTime(doiState.last_success_at) : 'never'}
                      </span>
                    </div>
                  ) : null}
                      </>
                    );
                  })()}
                </div>
                <a
                  href={journal.homepage_url}
                  target="_blank"
                  rel="noreferrer"
                  className="ghost-button"
                >
                  <ExternalLink size={16} strokeWidth={2.2} aria-hidden="true" />
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
