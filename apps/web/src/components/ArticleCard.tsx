import { Link } from 'react-router-dom';
import type { ArticleListItem } from '../api/types';
import { formatDate } from '../lib/utils';
import { AuthorList } from './AuthorList';

export function ArticleCard({ article }: { article: ArticleListItem }) {
  return (
    <article className="article-row">
      <div className="article-meta">
        <span>{article.journal.journal_name}</span>
        <span>{article.source_category.replace('_', ' ')}</span>
        <span>{formatDate(article.published_at)}</span>
      </div>
      <h3>
        <a href={article.url} target="_blank" rel="noreferrer" className="article-title-link">
          {article.title}
        </a>
      </h3>
      <AuthorList
        authors={article.authors}
        authorsText={article.authors_text}
        className="article-authors"
      />
      {article.abstract || article.snippet ? (
        <p className="article-snippet">{article.abstract ?? article.snippet}</p>
      ) : null}
      <div className="article-footer">
        {article.doi ? <span className="pill">DOI</span> : <span className="pill muted-pill">No DOI</span>}
        {article.article_type ? <span className="pill">{article.article_type}</span> : null}
        <Link to={`/articles/${article.id}`} className="pill muted-pill">
          Metadata
        </Link>
      </div>
    </article>
  );
}
