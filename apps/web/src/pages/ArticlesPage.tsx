import { startTransition } from 'react';
import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
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

  if (articlesQuery.isLoading || journalsQuery.isLoading) return <LoadingState label="Loading article index…" />;
  if (articlesQuery.isError || journalsQuery.isError || !articlesQuery.data || !journalsQuery.data) {
    return <ErrorState label="Article index could not be loaded." />;
  }

  return (
    <div className="page-stack">
      <section className="filter-grid">
        <select value={filters.journal ?? ''} onChange={(event) => updateFilter('journal', event.target.value)}>
          <option value="">All journals</option>
          {journalsQuery.data.map((journal) => (
            <option key={journal.slug} value={journal.slug}>
              {journal.journal_name}
            </option>
          ))}
        </select>
        <input
          type="text"
          placeholder="Author name"
          value={filters.author ?? ''}
          onChange={(event) => updateFilter('author', event.target.value)}
        />
        <select
          value={filters.sourceCategory ?? ''}
          onChange={(event) => updateFilter('sourceCategory', event.target.value)}
        >
          <option value="">All sources</option>
          <option value="current_issue">Current issue</option>
          <option value="online_first">Online first</option>
        </select>
        <input
          type="text"
          placeholder="Article type"
          value={filters.articleType ?? ''}
          onChange={(event) => updateFilter('articleType', event.target.value)}
        />
        <input type="date" value={filters.dateFrom ?? ''} onChange={(event) => updateFilter('dateFrom', event.target.value)} />
        <input type="date" value={filters.dateTo ?? ''} onChange={(event) => updateFilter('dateTo', event.target.value)} />
        <select value={filters.hasDoi ?? ''} onChange={(event) => updateFilter('hasDoi', event.target.value)}>
          <option value="">DOI: any</option>
          <option value="true">With DOI</option>
          <option value="false">Without DOI</option>
        </select>
        <select
          value={filters.hasAbstract ?? ''}
          onChange={(event) => updateFilter('hasAbstract', event.target.value)}
        >
          <option value="">Abstract: any</option>
          <option value="true">With abstract</option>
          <option value="false">Without abstract</option>
        </select>
      </section>

      <section className="panel">
        <div className="section-header">
          <div>
            <p className="eyebrow">Articles</p>
            <h2>{articlesQuery.data.meta.total} matching items</h2>
          </div>
        </div>

        <div className="list-stack">
          {articlesQuery.data.items.length ? (
            articlesQuery.data.items.map((article) => <ArticleCard key={article.id} article={article} />)
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
