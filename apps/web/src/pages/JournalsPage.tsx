import { formatDateTime } from '../lib/utils';
import { useQuery } from '@tanstack/react-query';
import { ExternalLink } from 'lucide-react';
import { Link } from 'react-router-dom';
import { getJournals } from '../api/client';
import { EmptyState, ErrorState, LoadingState } from '../components/States';

export function JournalsPage() {
  const journalsQuery = useQuery({ queryKey: ['journals'], queryFn: getJournals });

  if (journalsQuery.isLoading) return <LoadingState label="正在读取期刊…" />;
  if (journalsQuery.isError || !journalsQuery.data)
    return <ErrorState label="期刊配置读取失败，请重新加载。" />;

  return (
    <div className="page-stack">
      <section className="page-header">
        <div>
          <p className="eyebrow">文献来源</p>
          <h2>收录期刊</h2>
        </div>
        <p className="muted">每天更新已启用的期刊；暂停更新的期刊仍保留历史文章。</p>
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
                        <p className="muted">
                          {journal.enabled ? '自动更新中' : '已暂停更新 · 保留历史文章'}
                        </p>
                        {doiState ? (
                          <div className="article-footer">
                            <span className="pill">
                              最近成功同步：
                              {doiState.last_success_at
                                ? formatDateTime(doiState.last_success_at)
                                : '尚无记录'}
                            </span>
                          </div>
                        ) : null}
                      </>
                    );
                  })()}
                </div>
                <div className="settings-actions">
                  <Link className="ghost-button" to={`/articles?journal=${journal.slug}`}>
                    查看文章
                  </Link>
                  <a
                    href={journal.homepage_url}
                    target="_blank"
                    rel="noreferrer"
                    className="ghost-button"
                  >
                    <ExternalLink size={16} strokeWidth={2.2} aria-hidden="true" />
                    期刊官网
                  </a>
                </div>
              </article>
            ))
          ) : (
            <EmptyState label="暂无收录期刊" />
          )}
        </div>
      </section>
    </div>
  );
}
