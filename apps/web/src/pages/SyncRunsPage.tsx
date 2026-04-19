import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { getSyncRuns, runSync } from '../api/client';
import { isStaticMode } from '../lib/env';
import { formatDateTime } from '../lib/utils';
import { EmptyState, ErrorState, LoadingState } from '../components/States';

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
  if (syncRunsQuery.isError || !syncRunsQuery.data) return <ErrorState label="Sync history could not be loaded." />;

  return (
    <div className="page-stack">
      <section className="page-header">
        <div>
          <p className="eyebrow">Operations</p>
          <h2>Synchronization runs</h2>
        </div>
        {!isStaticMode ? (
          <button className="primary-button" onClick={() => syncMutation.mutate()} disabled={syncMutation.isPending}>
            {syncMutation.isPending ? 'Running sync…' : 'Run full sync now'}
          </button>
        ) : null}
      </section>

      <section className="panel">
        <div className="list-stack">
          {syncRunsQuery.data.length ? (
            syncRunsQuery.data.map((run) => (
              <article className="journal-panel" key={run.id}>
                <div>
                  <p className="eyebrow">{run.status}</p>
                  <h3>{run.scope}</h3>
                  <p className="muted">
                    Started {formatDateTime(run.started_at)} · Inserted {run.total_inserted} · Updated {run.total_updated}
                    {' · '}Failed {run.total_failed}
                  </p>
                </div>
                <div className="sync-meta">
                  <strong>{run.id.slice(0, 8)}</strong>
                  <span>{run.triggered_by}</span>
                </div>
              </article>
            ))
          ) : (
            <EmptyState label="No sync runs recorded yet." />
          )}
        </div>
      </section>
    </div>
  );
}

