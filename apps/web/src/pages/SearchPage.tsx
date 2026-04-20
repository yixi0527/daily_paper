import { startTransition, useDeferredValue, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import { getJournals, searchArticles } from '../api/client';
import { AuthorList } from '../components/AuthorList';
import { EmptyState, ErrorState, LoadingState } from '../components/States';
import { Pagination } from '../components/Pagination';
import { useRecentSearches } from '../hooks/useRecentSearches';

export function SearchPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const title = searchParams.get('title') ?? '';
  const author = searchParams.get('author') ?? '';
  const abstract = searchParams.get('abstract') ?? '';
  const [draftTitle, setDraftTitle] = useState(title);
  const [draftAuthor, setDraftAuthor] = useState(author);
  const [draftAbstract, setDraftAbstract] = useState(abstract);
  const deferredTitle = useDeferredValue(draftTitle);
  const { recent, remember } = useRecentSearches();

  const params = useMemo(
    () => ({
      title: searchParams.get('title') ?? undefined,
      author: searchParams.get('author') ?? undefined,
      abstract: searchParams.get('abstract') ?? undefined,
      journal: searchParams.get('journal') ?? undefined,
      dateFrom: searchParams.get('dateFrom') ?? undefined,
      dateTo: searchParams.get('dateTo') ?? undefined,
      page: Number(searchParams.get('page') ?? '1'),
      pageSize: 20,
    }),
    [searchParams],
  );

  const searchQuery = useQuery({
    queryKey: ['search', params],
    queryFn: () => searchArticles(params),
    enabled: Boolean(params.title || params.author || params.abstract),
  });
  const journalsQuery = useQuery({ queryKey: ['journals'], queryFn: getJournals });

  const updateParam = (key: string, value: string) => {
    const next = new URLSearchParams(searchParams);
    if (!value) next.delete(key);
    else next.set(key, value);
    if (key !== 'page') next.set('page', '1');
    startTransition(() => setSearchParams(next));
  };

  const submitSearch = () => {
    const next = new URLSearchParams(searchParams);
    if (deferredTitle) next.set('title', deferredTitle);
    else next.delete('title');
    if (draftAuthor) next.set('author', draftAuthor);
    else next.delete('author');
    if (draftAbstract) next.set('abstract', draftAbstract);
    else next.delete('abstract');
    next.set('page', '1');
    startTransition(() => setSearchParams(next));
    remember([deferredTitle, draftAuthor, draftAbstract].filter(Boolean).join(' | '));
  };

  if (journalsQuery.isLoading) return <LoadingState label="Loading search workspace…" />;
  if (journalsQuery.isError || !journalsQuery.data) return <ErrorState label="Search workspace could not be loaded." />;

  return (
    <div className="page-stack">
      <section className="page-header">
        <div>
          <p className="eyebrow">Search</p>
          <h2>Field-aware paper search</h2>
        </div>
        <p className="muted">Combine author, title, abstract, journal, and date filters. Recent queries stay local in this browser.</p>
      </section>

      <section className="search-grid">
        <input
          type="text"
          placeholder="Title keywords"
          value={draftTitle}
          onChange={(event) => setDraftTitle(event.target.value)}
        />
        <input
          type="text"
          placeholder="Author name"
          value={draftAuthor}
          onChange={(event) => setDraftAuthor(event.target.value)}
        />
        <input
          type="text"
          placeholder="Abstract keywords"
          value={draftAbstract}
          onChange={(event) => setDraftAbstract(event.target.value)}
        />
        <select defaultValue={params.journal ?? ''} onChange={(event) => updateParam('journal', event.target.value)}>
          <option value="">All journals</option>
          {journalsQuery.data.map((journal) => (
            <option key={journal.slug} value={journal.slug}>
              {journal.journal_name}
            </option>
          ))}
        </select>
        <input type="date" defaultValue={params.dateFrom ?? ''} onBlur={(event) => updateParam('dateFrom', event.target.value)} />
        <input type="date" defaultValue={params.dateTo ?? ''} onBlur={(event) => updateParam('dateTo', event.target.value)} />
        <button className="primary-button" onClick={submitSearch}>
          Search
        </button>
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

      {!params.title && !params.author && !params.abstract ? (
        <EmptyState label="Enter at least one field to search." />
      ) : searchQuery.isLoading ? (
        <LoadingState label="Running search…" />
      ) : searchQuery.isError || !searchQuery.data ? (
        <ErrorState label="Search failed." />
      ) : (
        <section className="panel">
          <div className="section-header">
            <div>
              <p className="eyebrow">Results</p>
              <h2>{searchQuery.data.meta.total} matching papers</h2>
            </div>
          </div>
          <div className="list-stack">
            {searchQuery.data.items.length ? (
              searchQuery.data.items.map((hit) => (
                <article className="article-row" key={hit.article.id}>
                  <div className="article-meta">
                    <span>{hit.article.journal.journal_name}</span>
                    <span>Score {hit.score}</span>
                  </div>
                  <h3>
                    <a
                      href={hit.article.url}
                      target="_blank"
                      rel="noreferrer"
                      className="article-title-link"
                      dangerouslySetInnerHTML={{ __html: hit.highlights.title || hit.article.title }}
                    />
                  </h3>
                  <AuthorList
                    authors={hit.article.authors}
                    authorsText={hit.article.authors_text}
                    className="article-authors"
                  />
                  <p
                    className="article-snippet"
                    dangerouslySetInnerHTML={{
                      __html: hit.highlights.abstract || hit.article.abstract || hit.article.snippet || '',
                    }}
                  />
                </article>
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
