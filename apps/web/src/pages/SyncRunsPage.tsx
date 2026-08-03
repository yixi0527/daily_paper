import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { RefreshCw } from 'lucide-react';
import { getSyncRuns, runSync } from '../api/client';
import { isStaticMode } from '../lib/env';
import { formatDateTime } from '../lib/utils';
import { EmptyState, ErrorState, LoadingState } from '../components/States';

function formatCategory(category: string) {
  return category.replace(/_/g, ' ');
}

export function SyncRunsPage() {
  const queryClient = useQueryClient();
  const syncRunsQuery = useQuery({ queryKey: ['sync-runs'], queryFn: getSyncRuns });
  const syncMutation = useMutation({
    mutationFn: () => runSync(),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['sync-runs'] });
      await queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      await queryClient.invalidateQueries({ queryKey: ['articles'] });
    },
  });

  if (syncRunsQuery.isLoading) return <LoadingState label="Loading sync history…" />;
  if (syncRunsQuery.isError || !syncRunsQuery.data)
    return <ErrorState label="Sync history could not be loaded." />;

  return (
    <div className="page-stack">
      <section className="page-header">
        <div>
          <p className="eyebrow">Operations</p>
          <h2>Synchronization runs</h2>
        </div>
        {!isStaticMode ? (
          <button
            className="primary-button"
            onClick={() => syncMutation.mutate()}
            disabled={syncMutation.isPending}
          >
            <RefreshCw size={16} strokeWidth={2.2} aria-hidden="true" />
            {syncMutation.isPending ? 'Running sync…' : 'Run full sync now'}
          </button>
        ) : null}
      </section>

      <section className="panel">
        <div className="list-stack">
          {syncRunsQuery.data.length ? (
            syncRunsQuery.data.map((run) => {
              const fetchedRuns = run.journal_runs.filter((journalRun) => journalRun.status === 'success');
              const failedRuns = run.journal_runs.filter((journalRun) => journalRun.status === 'failed');
              const unchangedRuns = run.journal_runs.filter(
                (journalRun) => journalRun.status === 'not_modified' || journalRun.status === 'skipped',
              );

              return (
                <article className="journal-panel sync-run-panel" key={run.id}>
                  <div className="sync-run-content">
                    <div>
                      <p className="eyebrow">{run.status}</p>
                      <h3>{run.scope}</h3>
                      <p className="muted">
                        Started {formatDateTime(run.started_at)} · Inserted {run.total_inserted} ·
                        Updated {run.total_updated}
                        {' · '}Failed {run.total_failed}
                      </p>
                    </div>

                    <div className="sync-result-groups">
                      <section className="sync-result-group" aria-label="Successfully fetched journals">
                        <h4>Fetched successfully</h4>
                        {fetchedRuns.length ? (
                          <ul>
                            {fetchedRuns.map((journalRun) => (
                              <li key={`${journalRun.journal_id}-${journalRun.source_category}`}>
                                <span>
                                  {journalRun.journal_name} · {formatCategory(journalRun.source_category)}
                                </span>
                                <strong>{journalRun.fetched_count} papers</strong>
                              </li>
                            ))}
                          </ul>
                        ) : (
                          <p className="muted">No papers were fetched in this run.</p>
                        )}
                      </section>

                      {failedRuns.length ? (
                        <section className="sync-result-group sync-result-group-failed" aria-label="Failed journals">
                          <h4>Failed</h4>
                          <ul>
                            {failedRuns.map((journalRun) => (
                              <li key={`${journalRun.journal_id}-${journalRun.source_category}`}>
                                <span>
                                  {journalRun.journal_name} · {formatCategory(journalRun.source_category)}
                                </span>
                                <p>{journalRun.error_message}</p>
                              </li>
                            ))}
                          </ul>
                        </section>
                      ) : null}

                      {unchangedRuns.length ? (
                        <section className="sync-result-group" aria-label="Journals with no new papers">
                          <h4>No new papers</h4>
                          <ul>
                            {unchangedRuns.map((journalRun) => (
                              <li key={`${journalRun.journal_id}-${journalRun.source_category}`}>
                                {journalRun.journal_name} · {formatCategory(journalRun.source_category)}
                              </li>
                            ))}
                          </ul>
                        </section>
                      ) : null}
                    </div>
                  </div>
                  <div className="sync-meta">
                    <strong>{run.id.slice(0, 8)}</strong>
                    <span>{run.triggered_by}</span>
                  </div>
                </article>
              );
            })
          ) : (
            <EmptyState label="No sync runs recorded yet." />
          )}
        </div>
      </section>
    </div>
  );
}
