import { Link } from 'react-router-dom';
import { ArrowRight, CalendarDays, ExternalLink, FileText } from 'lucide-react';
import type { ArticleListItem } from '../api/types';
import { formatDate } from '../lib/utils';
import { AuthorList } from './AuthorList';
import { FavoriteButton } from './FavoriteButton';

export function ArticleCard({ article }: { article: ArticleListItem }) {
  const primaryTitle = article.title_zh || article.title;
  const dateLabel = article.display_date_source === 'acquired' ? 'Acquired' : 'Published';
  const hasTranslation = Boolean(article.title_zh || article.abstract_zh);

  return (
    <article className="article-card">
      <div className="article-card-main">
        <div className="article-meta">
          <span className="meta-chip strong">{article.journal.journal_name}</span>
          <span className="meta-chip">
            <CalendarDays size={14} strokeWidth={2} aria-hidden="true" />
            {dateLabel} {formatDate(article.display_date)}
          </span>
          {hasTranslation ? (
            <span className="meta-chip translation-chip">中文翻译 · Codex Spark</span>
          ) : null}
        </div>

        <h3>
          <Link to={`/articles/${article.id}`} className="article-title-link">
            {primaryTitle}
          </Link>
        </h3>

        {article.title_zh ? <p className="article-original-title">{article.title}</p> : null}
        <AuthorList
          authors={article.authors}
          authorsText={article.authors_text}
          className="article-authors"
        />
        {article.abstract_zh ? (
          <div className="article-translation">
            <p className="translation-section-label">中文摘要</p>
            <p className="article-snippet article-snippet-zh">{article.abstract_zh}</p>
          </div>
        ) : null}
        {article.abstract || article.snippet ? (
          <details className="original-abstract">
            <summary>Original abstract</summary>
            <p className="article-snippet">{article.abstract ?? article.snippet}</p>
          </details>
        ) : null}
      </div>

      <div className="article-footer">
        <FavoriteButton articleKey={article.article_key} />
        <a href={article.url} target="_blank" rel="noreferrer" className="publisher-link">
          Publisher
          <ExternalLink size={15} strokeWidth={2} aria-hidden="true" />
        </a>
        <Link to={`/articles/${article.id}`} className="detail-link">
          <FileText size={15} strokeWidth={2} aria-hidden="true" />
          Details
          <ArrowRight size={15} strokeWidth={2} aria-hidden="true" />
        </Link>
      </div>
    </article>
  );
}
