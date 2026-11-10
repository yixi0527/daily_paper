import { useDeferredValue } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import { CalendarDays, Search, SlidersHorizontal, X } from 'lucide-react';
import { getAllArticles } from '../api/client';
import { ArticleCard } from '../components/ArticleCard';
import { ArticleReader } from '../components/ArticleReader';
import { EmptyState, ErrorState, LoadingState } from '../components/States';
import { Pagination } from '../components/Pagination';
import { useReadingStatus, type ReadingFilter } from '../hooks/useReadingStatus';
import { useFavorites } from '../hooks/useFavorites';
import { ReadingProgress } from '../components/ReadingProgress';
import { calendarDateKey, summarizeReadingByOnlineDate } from '../lib/readingCalendar';

export function ArticlesPage({
  readingFilter = 'all',
  favoritesOnly = false,
}: {
  readingFilter?: ReadingFilter;
  favoritesOnly?: boolean;
}) {
  const [params, setParams] = useSearchParams();
  const { isRead, setRead } = useReadingStatus();
  const { isFavorite } = useFavorites();
  const query = params.get('q') ?? '';
  const deferredQuery = useDeferredValue(query.trim().toLowerCase());
  const library = useQuery({
    queryKey: ['library'],
    queryFn: () => getAllArticles(),
    staleTime: 60000,
  });
  const update = (key: string, value: string | null) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    next.delete('page');
    next.delete('article');
    setParams(next, { replace: key === 'q' });
  };
  const openReader = (id: string | null) => {
    const next = new URLSearchParams(params);
    if (id) next.set('article', id);
    else next.delete('article');
    setParams(next, { replace: true });
  };
  if (library.isLoading) return <LoadingState label="正在打开文献库…" />;
  if (library.isError || !library.data)
    return (
      <div>
        <ErrorState
          label={library.error instanceof Error ? library.error.message : '文献库加载失败'}
        />
        <button className="primary-button" onClick={() => void library.refetch()}>
          重新加载
        </button>
      </div>
    );
  const journal = params.get('journal');
  const author = params.get('author');
  const date = params.get('date');
  const undated = params.get('undated') === '1';
  const selectedId = params.get('article');
  const journals = [
    ...new Map(library.data.map((article) => [article.journal.slug, article.journal])).values(),
  ].sort((a, b) => a.journal_name.localeCompare(b.journal_name));
  const base = library.data.filter((article) => {
    if (journal && article.journal.slug !== journal) return false;
    if (author && !(article.authors_text ?? '').toLowerCase().includes(author.toLowerCase()))
      return false;
    if (
      deferredQuery &&
      ![article.title, article.title_zh, article.authors_text, article.doi]
        .filter(Boolean)
        .join(' ')
        .toLowerCase()
        .includes(deferredQuery)
    )
      return false;
    return true;
  });
  const { dailyProgress, undatedCount } = summarizeReadingByOnlineDate(base, isRead);
  const completed = base.filter((article) => isRead(article.article_key)).length;
  const matching = base.filter((article) => {
    if (favoritesOnly && !isFavorite(article.article_key)) return false;
    if (readingFilter !== 'all' && isRead(article.article_key) !== (readingFilter === 'read'))
      return false;
    if (undated && article.online_published_at !== null) return false;
    if (
      date &&
      (article.online_published_at === null ||
        calendarDateKey(new Date(article.online_published_at)) !== date)
    )
      return false;
    return true;
  });
  const totalPages = Math.max(1, Math.ceil(matching.length / 20));
  const page = Math.min(Number(params.get('page') ?? '1'), totalPages);
  const visible = matching.slice((page - 1) * 20, page * 20);
  const title = favoritesOnly
    ? '收藏'
    : readingFilter === 'unread'
      ? '未读'
      : readingFilter === 'read'
        ? '已读'
        : '全部文章';
  const hasFilters = Boolean(query || journal || author || date || undated);
  const selectedIndex = matching.findIndex((article) => article.id === selectedId);
  const onChangeRead = (key: string, read: boolean) => {
    const next = matching[selectedIndex + 1]?.id ?? matching[selectedIndex - 1]?.id ?? null;
    setRead(key, read);
    if (readingFilter !== 'all') openReader(next);
  };
  return (
    <div className="library-page">
      <header className="library-heading">
        <div>
          <p className="eyebrow">你的文献库</p>
          <h1>
            {title}
            <span>{matching.length.toLocaleString('zh-CN')}</span>
          </h1>
          <p className="muted">从一篇开始，保持好奇。</p>
        </div>
        <span className="sort-label">Online 日期 · 从新到旧</span>
      </header>
      <section className="library-filters" aria-label="文章筛选">
        <label className="library-search">
          <Search size={19} />
          <input
            type="search"
            aria-label="搜索标题、作者或 DOI"
            placeholder="搜索标题、作者或 DOI…"
            value={query}
            onChange={(event) => update('q', event.target.value)}
          />
          {query ? (
            <button
              type="button"
              className="icon-button"
              aria-label="清除搜索"
              onClick={() => update('q', null)}
            >
              <X size={16} />
            </button>
          ) : null}
        </label>
        <label className="journal-select">
          <SlidersHorizontal size={17} />
          <select
            aria-label="筛选期刊"
            value={journal ?? ''}
            onChange={(event) => update('journal', event.target.value)}
          >
            <option value="">全部期刊</option>
            {journals.map((item) => (
              <option value={item.slug} key={item.slug}>
                {item.journal_name}
              </option>
            ))}
          </select>
        </label>
      </section>
      {hasFilters ? (
        <div className="active-filters">
          {author ? (
            <button onClick={() => update('author', null)}>
              作者：{author}
              <X size={13} />
            </button>
          ) : null}
          {date ? (
            <button onClick={() => update('date', null)}>
              <CalendarDays size={13} />
              {date}
              <X size={13} />
            </button>
          ) : null}
          {undated ? (
            <button onClick={() => update('undated', null)}>
              Online 日期缺失
              <X size={13} />
            </button>
          ) : null}
          <button className="clear-filter" onClick={() => setParams({})}>
            清除筛选
          </button>
        </div>
      ) : null}
      <ReadingProgress
        completed={completed}
        total={base.length}
        dailyProgress={dailyProgress}
        undatedCount={undatedCount}
        filtered={Boolean(journal || author || query)}
        filterDate={date}
        onDateSelect={(value) => {
          const next = new URLSearchParams(params);
          next.delete('undated');
          next.delete('page');
          if (value === date) next.delete('date');
          else next.set('date', value);
          setParams(next);
        }}
        onUndatedSelect={() => {
          const next = new URLSearchParams(params);
          next.delete('date');
          next.delete('page');
          next.set('undated', '1');
          setParams(next);
        }}
      />
      <div className="feed-heading">
        <span>{hasFilters ? '筛选结果' : '文章列表'}</span>
        <span>
          {matching.length} 篇{page > 1 ? ` · 第 ${page} 页` : ''}
        </span>
      </div>
      <section className="paper-feed" aria-label={`${title}文章`}>
        {visible.length ? (
          visible.map((article) => <ArticleCard key={article.article_key} article={article} />)
        ) : (
          <EmptyState
            label={
              readingFilter === 'unread' && !hasFilters
                ? '未读已清空，做得很好。'
                : favoritesOnly && !hasFilters
                  ? '还没有收藏的文章'
                  : '没有符合条件的文章'
            }
            hint={
              hasFilters
                ? '试试更换关键词或清除筛选。'
                : favoritesOnly
                  ? '点击文章右上角的爱心，留给下次细读。'
                  : '可以查看全部文章，或等下一次自动更新。'
            }
          />
        )}
      </section>
      {matching.length > 20 ? (
        <Pagination
          page={page}
          totalPages={totalPages}
          onPageChange={(nextPage) => {
            const next = new URLSearchParams(params);
            next.set('page', String(nextPage));
            setParams(next);
            window.scrollTo({ top: 0, behavior: 'smooth' });
          }}
        />
      ) : null}
      {selectedId ? (
        <ArticleReader
          articleId={selectedId}
          onClose={() => openReader(null)}
          onRead={onChangeRead}
          readAndNext={readingFilter === 'unread'}
          previousId={matching[selectedIndex - 1]?.id}
          nextId={matching[selectedIndex + 1]?.id}
          onNavigate={openReader}
        />
      ) : null}
    </div>
  );
}
