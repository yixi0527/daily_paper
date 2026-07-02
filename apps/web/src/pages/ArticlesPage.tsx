import { startTransition } from 'react';
import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import { Filter, X } from 'lucide-react';
import { getJournals, listArticles } from '../api/client';
import { ArticleCard } from '../components/ArticleCard';
import { EmptyState, ErrorState, LoadingState } from '../components/States';
import { Pagination } from '../components/Pagination';

export function ArticlesPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const page = Number(searchParams.get('page') ?? '1');
  const filters = useMemo(
    () => ({
      page,
      pageSize: 20,
      journal: searchParams.get('journal') ?? undefined,
      author: searchParams.get('author') ?? undefined,
      dateFrom: searchParams.get('dateFrom') ?? undefined,
      dateTo: searchParams.get('dateTo') ?? undefined,
      sourceCategory: searchParams.get('sourceCategory') ?? undefined,
      articleType: searchParams.get('articleType') ?? undefined,
      hasDoi: searchParams.get('hasDoi') ?? undefined,
      hasAbstract: searchParams.get('hasAbstract') ?? undefined,
    }),
    [page, searchParams],
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
  };

  const clearFilters = () => {
    startTransition(() => setSearchParams(new URLSearchParams()));
  };

  const activeFilterCount = [
    filters.journal,
    filters.author,
    filters.dateFrom,
    filters.dateTo,
    filters.sourceCategory,
    filters.articleType,
    filters.hasDoi,
    filters.hasAbstract,
  ].filter(Boolean).length;

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
      <section className="page-header">
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
          <label className="field">
            <span>Source</span>
            <select
              value={filters.sourceCategory ?? ''}
              onChange={(event) => updateFilter('sourceCategory', event.target.value)}
            >
              <option value="">All sources</option>
              <option value="current_issue">Current issue</option>
              <option value="online_first">Online first</option>
            </select>
          </label>
          <label className="field">
            <span>Article type</span>
            <input
              type="text"
              placeholder="Review, Article..."
              value={filters.articleType ?? ''}
              onChange={(event) => updateFilter('articleType', event.target.value)}
            />
          </label>
          <label className="field">
            <span>Published after</span>
            <input
              type="date"
              value={filters.dateFrom ?? ''}
              onChange={(event) => updateFilter('dateFrom', event.target.value)}
            />
          </label>
          <label className="field">
            <span>Published before</span>
            <input
              type="date"
              value={filters.dateTo ?? ''}
              onChange={(event) => updateFilter('dateTo', event.target.value)}
            />
          </label>
          <label className="field">
            <span>DOI</span>
            <select
              value={filters.hasDoi ?? ''}
              onChange={(event) => updateFilter('hasDoi', event.target.value)}
            >
              <option value="">Any</option>
              <option value="true">With DOI</option>
              <option value="false">Without DOI</option>
            </select>
          </label>
          <label className="field">
            <span>Abstract</span>
            <select
              value={filters.hasAbstract ?? ''}
              onChange={(event) => updateFilter('hasAbstract', event.target.value)}
            >
              <option value="">Any</option>
              <option value="true">With abstract</option>
              <option value="false">Without abstract</option>
            </select>
          </label>
        </div>
      </section>

      <section className="panel">
        <div className="list-stack">
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
