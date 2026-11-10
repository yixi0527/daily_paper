import { Link, useLocation } from 'react-router-dom';
import { ArrowUpRight, Check, Circle } from 'lucide-react';
import type { ArticleListItem } from '../api/types';
import { formatDate } from '../lib/utils';
import { useReadingStatus } from '../hooks/useReadingStatus';
import { FavoriteButton } from './FavoriteButton';

export function ArticleCard({ article }: { article: ArticleListItem }) {
  const { language, isRead, toggleRead } = useReadingStatus();
  const location = useLocation();
  const params = new URLSearchParams(location.search);
  params.set('article', article.id);
  const read = isRead(article.article_key);
  const title = language === 'zh' && article.title_zh ? article.title_zh : article.title;
  const excerpt = language === 'zh' ? article.abstract_zh : (article.abstract ?? article.snippet);
  const authorNames = article.authors
    .slice(0, 3)
    .map((author) => author.full_name)
    .join(' · ');
  return (
    <article className={`paper-card${read ? ' is-read' : ''}`}>
      <button
        type="button"
        className={`paper-read-toggle${read ? ' active' : ''}`}
        aria-label={read ? '设为未读' : '标记已读'}
        title={read ? '设为未读' : '标记已读'}
        aria-pressed={read}
        onClick={() => toggleRead(article.article_key)}
      >
        {read ? <Check size={20} /> : <Circle size={20} />}
      </button>
      <div className="paper-card-body">
        <div className="paper-meta">
          <Link
            to={`/articles?journal=${encodeURIComponent(article.journal.slug)}`}
            className="journal-label"
          >
            {article.journal.journal_name}
          </Link>
          <span className="paper-online">
            {article.online_published_at === null
              ? 'Online 日期缺失'
              : `Online ${formatDate(article.online_published_at)}`}
          </span>
        </div>
        <h3>
          <Link
            className="paper-title"
            to={{ pathname: location.pathname, search: params.toString() }}
          >
            {title}
          </Link>
        </h3>
        {language === 'zh' && article.title_zh ? (
          <p className="paper-original-title">{article.title}</p>
        ) : null}
        <p className="paper-authors">
          {authorNames || article.authors_text || '作者信息未提供'}
          {article.authors.length > 3 ? ' 等' : ''}
        </p>
        {excerpt ? (
          <p className="paper-excerpt">{excerpt}</p>
        ) : (
          <p className="paper-excerpt empty-excerpt">
            {language === 'zh' && !article.title_zh
              ? '中文译文尚未提供'
              : '暂无摘要预览，查看出版页面了解更多。'}
          </p>
        )}
        <div className="paper-card-footer">
          <span>DOI {article.doi}</span>
          <a href={article.url} target="_blank" rel="noreferrer">
            出版页面
            <ArrowUpRight size={14} />
          </a>
        </div>
      </div>
      <FavoriteButton articleKey={article.article_key} compact />
    </article>
  );
}
