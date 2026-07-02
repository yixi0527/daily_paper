import { Link } from 'react-router-dom';
import { ArrowRight, CalendarDays, ExternalLink, FileText } from 'lucide-react';
import type { ArticleListItem } from '../api/types';
import { formatDate } from '../lib/utils';
import { AuthorList } from './AuthorList';

export function ArticleCard({ article }: { article: ArticleListItem }) {
  const sourceCategory = article.source_category.replace('_', ' ');

  return (
    <article className="article-card">
      <div className="article-card-main">
        <div className="article-meta">
          <span className="meta-chip strong">{article.journal.journal_name}</span>
          <span className="meta-chip">{sourceCategory}</span>
          <span className="meta-chip">
            <CalendarDays size={14} strokeWidth={2} aria-hidden="true" />
            {formatDate(article.published_at)}
          </span>
        </div>

        <h3>
          <a href={article.url} target="_blank" rel="noreferrer" className="article-title-link">
            {article.title}
            <ExternalLink size={16} strokeWidth={2} aria-hidden="true" />
          </a>
        </h3>

        {article.title_zh ? <p className="article-title-zh">{article.title_zh}</p> : null}
        <AuthorList
          authors={article.authors}
          authorsText={article.authors_text}
          className="article-authors"
        />
        {article.abstract_zh ? (
          <p className="article-snippet article-snippet-zh">{article.abstract_zh}</p>
        ) : null}
        {article.abstract || article.snippet ? (
          <p className="article-snippet">{article.abstract ?? article.snippet}</p>
        ) : null}
      </div>

      <div className="article-footer">
        {article.doi ? (
          <span className="pill">DOI</span>
        ) : (
          <span className="pill muted-pill">No DOI</span>
        )}
        {article.article_type ? <span className="pill">{article.article_type}</span> : null}
        {article.analysis_generated_at ? <span className="pill">中文解读</span> : null}
        <Link to={`/articles/${article.id}`} className="detail-link">
          <FileText size={15} strokeWidth={2} aria-hidden="true" />
          Metadata
          <ArrowRight size={15} strokeWidth={2} aria-hidden="true" />
        </Link>
      </div>
    </article>
  );
}
