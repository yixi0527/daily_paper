import { startTransition } from 'react';
import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import { Filter, X } from 'lucide-react';
import { getJournals, listArticles } from '../api/client';
import { ArticleCard } from '../components/ArticleCard';
import { EmptyState, ErrorState, LoadingState } from '../components/States';
import { Pagination } from '../components/Pagination';
import { useMediaQuery } from '../hooks/useMediaQuery';

export function ArticlesPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const isMobile = useMediaQuery('(max-width: 680px)');
  const page = Number(searchParams.get('page') ?? '1');
  const pageSize = isMobile ? 1 : 20;
  const filters = useMemo(
    () => ({
      page,
      pageSize,
      journal: searchParams.get('journal') ?? undefined,
      author: searchParams.get('author') ?? undefined,
    }),
    [page, pageSize, searchParams],
  );

  const articlesQuery = useQuery({
    queryKey: ['articles', filters],
    queryFn: () => listArticles(filters),
  });
  const journalsQuery = useQuery({ queryKey: ['journals'], queryFn: getJournals });

  const updateFilter = (key: string, value: string) => {
    const next = new URLSearchParams(searchParams);
    if (!value) next.delete(key);
    else next.set(key, value);
    if (key !== 'page') next.set('page', '1');
    startTransition(() => setSearchParams(next));
    if (key === 'page') window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const clearFilters = () => {
    startTransition(() => setSearchParams(new URLSearchParams()));
  };

  const activeFilterCount = [filters.journal, filters.author].filter(Boolean).length;

  if (articlesQuery.isLoading || journalsQuery.isLoading)
    return <LoadingState label="Loading article index…" />;
  if (
    articlesQuery.isError ||
    journalsQuery.isError ||
    !articlesQuery.data ||
    !journalsQuery.data
  ) {
    return <ErrorState label="Article index could not be loaded." />;
  }

  return (
    <div className="page-stack">
      <section className="page-header compact-page-header">
        <div>
          <p className="eyebrow">Article index</p>
          <h2>{articlesQuery.data.meta.total} matching papers</h2>
        </div>
        <div className="header-actions">
          <span className="mode-pill">
            <Filter size={15} strokeWidth={2.1} aria-hidden="true" />
            {activeFilterCount} active filters
          </span>
          {activeFilterCount ? (
            <button type="button" className="ghost-button" onClick={clearFilters}>
              <X size={16} strokeWidth={2.2} aria-hidden="true" />
              Clear
            </button>
          ) : null}
        </div>
      </section>

      <section className="filter-panel">
        <div className="filter-grid">
          <label className="field">
            <span>Journal</span>
            <select
              value={filters.journal ?? ''}
              onChange={(event) => updateFilter('journal', event.target.value)}
            >
              <option value="">All journals</option>
              {journalsQuery.data.map((journal) => (
                <option key={journal.slug} value={journal.slug}>
                  {journal.journal_name}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>Author</span>
            <input
              type="text"
              placeholder="Author name"
              value={filters.author ?? ''}
              onChange={(event) => updateFilter('author', event.target.value)}
            />
          </label>
        </div>
      </section>

      <section className="panel article-feed-panel">
        <div className="list-stack focused-list">
          {articlesQuery.data.items.length ? (
            articlesQuery.data.items.map((article) => (
              <ArticleCard key={article.id} article={article} />
            ))
          ) : (
            <EmptyState label="No articles match the current filters." />
          )}
        </div>

        <Pagination
          page={articlesQuery.data.meta.page}
          totalPages={articlesQuery.data.meta.total_pages}
          onPageChange={(nextPage) => updateFilter('page', String(nextPage))}
        />
      </section>
    </div>
  );
}
