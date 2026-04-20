import { useQuery } from '@tanstack/react-query';
import { useParams } from 'react-router-dom';
import { getArticle } from '../api/client';
import { AuthorList } from '../components/AuthorList';
import { CopyButton } from '../components/CopyButton';
import { EmptyState, ErrorState, LoadingState } from '../components/States';
import { formatDate } from '../lib/utils';
import { isStaticMode } from '../lib/env';

export function ArticleDetailPage() {
  const { articleId = '' } = useParams();
  const articleQuery = useQuery({
    queryKey: ['article', articleId],
    queryFn: () => getArticle(articleId),
  });

  if (articleQuery.isLoading) return <LoadingState label="Loading article detail…" />;
  if (articleQuery.isError) return <ErrorState label="Article detail could not be loaded." />;
  if (!articleQuery.data) return <EmptyState label="Article not found." />;

  const article = articleQuery.data;

  return (
    <div className="page-stack">
      <section className="page-header">
        <div>
          <p className="eyebrow">{article.journal.journal_name}</p>
          <h2>{article.title}</h2>
        </div>
        <div className="detail-actions">
          {article.doi ? <CopyButton value={article.doi} /> : null}
          <a href={article.url} target="_blank" rel="noreferrer" className="primary-link">
            Open publisher page
          </a>
        </div>
      </section>

      <section className="detail-grid">
        <div className="panel">
          <div className="detail-list">
            <div>
              <span>Authors</span>
              <AuthorList
                authors={article.authors}
                authorsText={article.authors_text}
                className="detail-authors"
              />
            </div>
            <div>
              <span>Published</span>
              <strong>{formatDate(article.published_at)}</strong>
            </div>
            <div>
              <span>DOI</span>
              <strong>{article.doi ?? 'Unavailable'}</strong>
            </div>
            <div>
              <span>Issue / volume</span>
              <strong>
                {article.volume ?? '–'} / {article.issue ?? '–'}
              </strong>
            </div>
            <div>
              <span>Article type</span>
              <strong>{article.article_type ?? 'Unknown'}</strong>
            </div>
            <div>
              <span>Source category</span>
              <strong>{article.source_category}</strong>
            </div>
          </div>
        </div>

        <div className="panel">
          <div className="section-header">
            <div>
              <p className="eyebrow">Abstract</p>
              <h2>Summary metadata</h2>
            </div>
          </div>
          <p className="detail-abstract">{article.abstract ?? article.snippet ?? 'No abstract available from source metadata.'}</p>
        </div>
      </section>

      {(import.meta.env.DEV || isStaticMode) && article.raw_payload ? (
        <section className="panel">
          <div className="section-header">
            <div>
              <p className="eyebrow">Debug</p>
              <h2>Raw payload</h2>
            </div>
          </div>
          <pre className="code-block">{JSON.stringify(article.raw_payload, null, 2)}</pre>
        </section>
      ) : null}
    </div>
  );
}
