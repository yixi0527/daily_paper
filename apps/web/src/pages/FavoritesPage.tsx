import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import { Heart } from 'lucide-react';
import { getFavoriteArticles } from '../api/client';
import { ArticleCard } from '../components/ArticleCard';
import { EmptyState, ErrorState, LoadingState } from '../components/States';
import { Pagination } from '../components/Pagination';
import { useFavorites } from '../hooks/useFavorites';
import { useMediaQuery } from '../hooks/useMediaQuery';

export function FavoritesPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const requestedPage = Number(searchParams.get('page') ?? '1');
  const isMobile = useMediaQuery('(max-width: 680px)');
  const pageSize = isMobile ? 1 : 20;
  const { favoriteKeys } = useFavorites();
  const stableFavoriteKeys = useMemo(() => [...favoriteKeys].sort(), [favoriteKeys]);
  const favoritesQuery = useQuery({
    queryKey: ['favorite-articles', stableFavoriteKeys],
    queryFn: () => getFavoriteArticles(stableFavoriteKeys),
    enabled: stableFavoriteKeys.length > 0,
  });

  if (!stableFavoriteKeys.length) {
    return (
      <EmptyState
        label="No saved papers yet."
        hint="Use the heart button on any paper to keep it in this browser."
      />
    );
  }
  if (favoritesQuery.isLoading) return <LoadingState label="Loading saved papers…" />;
  if (favoritesQuery.isError || !favoritesQuery.data) {
    return <ErrorState label="Saved papers could not be loaded." />;
  }

  const totalPages = Math.max(1, Math.ceil(favoritesQuery.data.length / pageSize));
  const page = Math.min(requestedPage, totalPages);
  const pageStart = (page - 1) * pageSize;
  const visibleArticles = favoritesQuery.data.slice(pageStart, pageStart + pageSize);
  const updatePage = (nextPage: number) => {
    const next = new URLSearchParams(searchParams);
    next.set('page', String(nextPage));
    setSearchParams(next);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <div className="page-stack">
      <section className="page-header compact-page-header">
        <div>
          <p className="eyebrow">Personal library</p>
          <h2>
            <Heart size={22} fill="currentColor" aria-hidden="true" />
            {favoritesQuery.data.length} saved papers
          </h2>
        </div>
      </section>

      <section className="panel article-feed-panel">
        <div className="list-stack focused-list">
          {visibleArticles.map((article) => (
            <ArticleCard key={article.article_key} article={article} />
          ))}
        </div>
        <Pagination page={page} totalPages={totalPages} onPageChange={updatePage} />
      </section>
    </div>
  );
}
