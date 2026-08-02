import { startTransition, useDeferredValue, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import { Search } from 'lucide-react';
import { getJournals, searchArticles } from '../api/client';
import { ArticleCard } from '../components/ArticleCard';
import { EmptyState, ErrorState, LoadingState } from '../components/States';
import { Pagination } from '../components/Pagination';
import { useRecentSearches } from '../hooks/useRecentSearches';
import { useMediaQuery } from '../hooks/useMediaQuery';

export function SearchPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const title = searchParams.get('title') ?? '';
  const author = searchParams.get('author') ?? '';
  const [draftTitle, setDraftTitle] = useState(title);
  const [draftAuthor, setDraftAuthor] = useState(author);
  const deferredTitle = useDeferredValue(draftTitle);
  const isMobile = useMediaQuery('(max-width: 680px)');
  const { recent, remember } = useRecentSearches();

  const params = useMemo(
    () => ({
      title: searchParams.get('title') ?? undefined,
      author: searchParams.get('author') ?? undefined,
      journal: searchParams.get('journal') ?? undefined,
      page: Number(searchParams.get('page') ?? '1'),
      pageSize: isMobile ? 1 : 20,
    }),
    [isMobile, searchParams],
  );

  const searchQuery = useQuery({
    queryKey: ['search', params],
    queryFn: () => searchArticles(params),
    enabled: Boolean(params.title || params.author),
  });
  const journalsQuery = useQuery({ queryKey: ['journals'], queryFn: getJournals });

  const updateParam = (key: string, value: string) => {
    const next = new URLSearchParams(searchParams);
    if (!value) next.delete(key);
    else next.set(key, value);
    if (key !== 'page') next.set('page', '1');
    startTransition(() => setSearchParams(next));
    if (key === 'page') window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const submitSearch = () => {
    const next = new URLSearchParams(searchParams);
    if (deferredTitle) next.set('title', deferredTitle);
    else next.delete('title');
    if (draftAuthor) next.set('author', draftAuthor);
    else next.delete('author');
    next.delete('abstract');
    next.delete('dateFrom');
    next.delete('dateTo');
    next.set('page', '1');
    startTransition(() => setSearchParams(next));
    remember([deferredTitle, draftAuthor].filter(Boolean).join(' | '));
  };

  if (journalsQuery.isLoading) return <LoadingState label="Loading search workspace…" />;
  if (journalsQuery.isError || !journalsQuery.data)
    return <ErrorState label="Search workspace could not be loaded." />;

  return (
    <div className="page-stack">
      <section className="page-header compact-page-header">
        <div>
          <p className="eyebrow">Search</p>
          <h2>Field-aware paper search</h2>
        </div>
        <p className="muted">
          Search by title, author, or journal. Recent queries stay local in this browser.
        </p>
      </section>

      <section className="filter-panel">
        <div className="search-grid">
          <label className="field field-wide">
            <span>Title</span>
            <input
              type="text"
              placeholder="Title keywords"
              value={draftTitle}
              onChange={(event) => setDraftTitle(event.target.value)}
            />
          </label>
          <label className="field">
            <span>Author</span>
            <input
              type="text"
              placeholder="Author name"
              value={draftAuthor}
              onChange={(event) => setDraftAuthor(event.target.value)}
            />
          </label>
          <label className="field">
            <span>Journal</span>
            <select
              defaultValue={params.journal ?? ''}
              onChange={(event) => updateParam('journal', event.target.value)}
            >
              <option value="">All journals</option>
              {journalsQuery.data.map((journal) => (
                <option key={journal.slug} value={journal.slug}>
                  {journal.journal_name}
                </option>
              ))}
            </select>
          </label>
          <button type="button" className="primary-button search-submit" onClick={submitSearch}>
            <Search size={17} strokeWidth={2.2} aria-hidden="true" />
            Search
          </button>
        </div>
      </section>

      {recent.length ? (
        <section className="panel">
          <div className="section-header">
            <div>
              <p className="eyebrow">Recent</p>
              <h2>Local search history</h2>
            </div>
          </div>
          <div className="recent-searches">
            {recent.map((entry) => (
              <button key={entry} className="ghost-button" onClick={() => setDraftTitle(entry)}>
                {entry}
              </button>
            ))}
          </div>
        </section>
      ) : null}

      {!params.title && !params.author ? (
        <EmptyState label="Enter at least one field to search." />
      ) : searchQuery.isLoading ? (
        <LoadingState label="Running search…" />
      ) : searchQuery.isError || !searchQuery.data ? (
        <ErrorState label="Search failed." />
      ) : (
        <section className="panel article-feed-panel">
          <div className="section-header">
            <div>
              <p className="eyebrow">Results</p>
              <h2>{searchQuery.data.meta.total} matching papers</h2>
            </div>
          </div>
          <div className="list-stack focused-list">
            {searchQuery.data.items.length ? (
              searchQuery.data.items.map((hit) => (
                <ArticleCard key={hit.article.article_key} article={hit.article} />
              ))
            ) : (
              <EmptyState label="No matches found." />
            )}
          </div>
          <Pagination
            page={searchQuery.data.meta.page}
            totalPages={searchQuery.data.meta.total_pages}
            onPageChange={(nextPage) => updateParam('page', String(nextPage))}
          />
        </section>
      )}
    </div>
  );
}
