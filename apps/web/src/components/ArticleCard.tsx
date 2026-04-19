import { Link } from 'react-router-dom';
import type { ArticleListItem } from '../api/types';
import { formatDate } from '../lib/utils';

export function ArticleCard({ article }: { article: ArticleListItem }) {
  return (
    <article className="article-row">
      <div className="article-meta">
        <span>{article.journal.journal_name}</span>
        <span>{article.source_category.replace('_', ' ')}</span>
        <span>{formatDate(article.published_at)}</span>
      </div>
      <h3>
        <Link to={`/articles/${article.id}`}>{article.title}</Link>
      </h3>
      <p className="article-authors">{article.authors_text || 'Author metadata unavailable'}</p>
      {article.snippet ? <p className="article-snippet">{article.snippet}</p> : null}
      <div className="article-footer">
        {article.doi ? <span className="pill">DOI</span> : <span className="pill muted-pill">No DOI</span>}
        {article.article_type ? <span className="pill">{article.article_type}</span> : null}
      </div>
    </article>
  );
}

