import { useQuery } from '@tanstack/react-query';
import { useParams } from 'react-router-dom';
import { ExternalLink } from 'lucide-react';
import { getArticle } from '../api/client';
import { AuthorList } from '../components/AuthorList';
import { CopyButton } from '../components/CopyButton';
import { FavoriteButton } from '../components/FavoriteButton';
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
  const dateLabel = article.display_date_source === 'acquired' ? 'Acquired' : 'Published';

  return (
    <div className="page-stack">
      <section className="page-header article-detail-header">
        <div>
          <p className="eyebrow">{article.journal.journal_name}</p>
          <h2>{article.title_zh || article.title}</h2>
          {article.title_zh ? (
            <p className="article-detail-original-title">{article.title}</p>
          ) : null}
        </div>
        <div className="detail-actions">
          <FavoriteButton articleKey={article.article_key} />
          {article.doi ? <CopyButton value={article.doi} /> : null}
          <a href={article.url} target="_blank" rel="noreferrer" className="primary-link">
            <ExternalLink size={16} strokeWidth={2.2} aria-hidden="true" />
            Publisher
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
              <span>{dateLabel}</span>
              <strong>{formatDate(article.display_date)}</strong>
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
          </div>
        </div>

        <div className="panel translation-panel">
          <div className="section-header">
            <div>
              <p className="eyebrow">中文译文</p>
              <h2>摘要</h2>
            </div>
            {article.translated_at ? (
              <span className="pill muted-pill">{formatDate(article.translated_at)}</span>
            ) : null}
          </div>
          {article.abstract_zh ? (
            <p className="detail-abstract detail-abstract-zh">{article.abstract_zh}</p>
          ) : (
            <p className="muted">该文献尚无可显示的中文摘要。</p>
          )}
        </div>
      </section>

      <section className="panel">
        <div className="section-header">
          <div>
            <p className="eyebrow">Original abstract</p>
            <h2>Source text</h2>
          </div>
          {article.translation_model ? (
            <span className="pill muted-pill">{article.translation_model}</span>
          ) : null}
        </div>
        <p className="detail-abstract">
          {article.abstract ?? article.snippet ?? 'No abstract available from source metadata.'}
        </p>
      </section>

      {(import.meta.env.DEV || isStaticMode) && article.raw_payload ? (
        <details className="panel raw-payload-panel">
          <summary>Raw source metadata</summary>
          <pre className="code-block">{JSON.stringify(article.raw_payload, null, 2)}</pre>
        </details>
      ) : null}
    </div>
  );
}
