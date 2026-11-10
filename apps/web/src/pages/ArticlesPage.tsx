import { startTransition } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import { getAllArticles } from '../api/client';
import { ArticleCard } from '../components/ArticleCard';
import { EmptyState, ErrorState, LoadingState } from '../components/States';
import { Pagination } from '../components/Pagination';
import { useMediaQuery } from '../hooks/useMediaQuery';
import { useReadingStatus } from '../hooks/useReadingStatus';
import { ReadingProgress } from '../components/ReadingProgress';

export function ArticlesPage({ readOnly = false }: { readOnly?: boolean }) {
  const [searchParams, setSearchParams] = useSearchParams();
  const isMobile = useMediaQuery('(max-width: 680px)');
  const { isRead } = useReadingStatus();
  const requestedPage = Number(searchParams.get('page') ?? '1');
  const pageSize = isMobile ? 1 : 20;
  const journal = searchParams.get('journal') ?? undefined;
  const author = searchParams.get('author') ?? undefined;

  const articlesQuery = useQuery({
    queryKey: ['article-library', journal, author],
    queryFn: () => getAllArticles({ journal, author }),
  });
  const updatePage = (page: number) => {
    const next = new URLSearchParams(searchParams);
    next.set('page', String(page));
    startTransition(() => setSearchParams(next));
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  if (articlesQuery.isLoading) return <LoadingState label="Loading articles…" />;
  if (articlesQuery.isError || !articlesQuery.data) {
    return <ErrorState label="Articles could not be loaded." />;
  }

  const articles = articlesQuery.data;
  const readCount = articles.reduce(
    (count, article) => count + Number(isRead(article.article_key)),
    0,
  );
  const matchingArticles = readOnly
    ? articles.filter((article) => isRead(article.article_key))
    : articles;
  const totalPages = Math.max(1, Math.ceil(matchingArticles.length / pageSize));
  const page = Math.min(requestedPage, totalPages);
  const visibleArticles = matchingArticles.slice((page - 1) * pageSize, page * pageSize);
  const categoryParams = new URLSearchParams(searchParams);
  categoryParams.delete('page');

  return (
    <div className="page-stack">
      <ReadingProgress
        completed={readCount}
        total={articles.length}
        filtered={Boolean(journal || author)}
        readOnly={readOnly}
        search={categoryParams.toString()}
      />
      {readOnly ? (
        <div className="read-list-heading">
          <h2>已读文章</h2>
          <span>{matchingArticles.length} 篇</span>
        </div>
      ) : null}
      <section className="panel article-feed-panel">
        <div className="list-stack focused-list">
          {visibleArticles.length ? (
            visibleArticles.map((article) => (
              <ArticleCard key={article.article_key} article={article} />
            ))
          ) : (
            <EmptyState
              label={readOnly ? '还没有已读文章' : 'No articles match the current filters.'}
              hint={readOnly ? '点击文章卡片上的“标记已读”，即可在这里查看。' : undefined}
            />
          )}
        </div>

        <Pagination page={page} totalPages={totalPages} onPageChange={updatePage} />
      </section>
    </div>
  );
}
