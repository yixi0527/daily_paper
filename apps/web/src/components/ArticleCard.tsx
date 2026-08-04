import { Link } from 'react-router-dom';
import { CalendarDays, ExternalLink } from 'lucide-react';
import type { ArticleListItem } from '../api/types';
import { formatDate } from '../lib/utils';
import { ArticleTranslationToggle } from './ArticleTranslationToggle';
import { AuthorList } from './AuthorList';
import { FavoriteButton } from './FavoriteButton';

export function ArticleCard({ article }: { article: ArticleListItem }) {
  const dateLabel = article.display_date_source === 'acquired' ? 'Acquired' : 'Published';
  const sourceAbstract = article.abstract ?? article.snippet;

  return (
    <article className="article-card">
      <div className="article-card-main">
        <div className="article-meta">
          <span className="meta-chip strong">{article.journal.journal_name}</span>
          <span className="meta-chip">
            <CalendarDays size={14} strokeWidth={2} aria-hidden="true" />
            {dateLabel} {formatDate(article.display_date)}
          </span>
        </div>

        <h3>
          <Link to={`/articles/${article.id}`} className="article-title-link">
            {article.title}
          </Link>
        </h3>

        <AuthorList
          authors={article.authors}
          authorsText={article.authors_text}
          className="article-authors"
        />
        {sourceAbstract ? <p className="article-snippet">{sourceAbstract}</p> : null}
        <ArticleTranslationToggle
          titleZh={article.title_zh}
          abstractZh={article.abstract_zh}
          variant="card"
        />
      </div>

      <div className="article-footer">
        <FavoriteButton articleKey={article.article_key} />
        <a href={article.url} target="_blank" rel="noreferrer" className="publisher-link">
          Publisher
          <ExternalLink size={15} strokeWidth={2} aria-hidden="true" />
        </a>
      </div>
    </article>
  );
}
