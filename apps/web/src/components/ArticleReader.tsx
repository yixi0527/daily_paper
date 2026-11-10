import { useEffect, useRef, type ElementRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ArrowLeft, ArrowRight, ArrowUpRight, CheckCheck, Circle, X } from 'lucide-react';
import type { ArticleDetail } from '../api/types';
import { getArticle } from '../api/client';
import { useReadingStatus } from '../hooks/useReadingStatus';
import { formatDate } from '../lib/utils';
import { FavoriteButton } from './FavoriteButton';
import { AuthorList } from './AuthorList';
import { CopyButton } from './CopyButton';
import { EmptyState, ErrorState, LoadingState } from './States';

export function ArticleReaderContent({
  article,
  onRead,
  readAndNext = false,
}: {
  article: ArticleDetail;
  onRead: (key: string, read: boolean) => void;
  readAndNext?: boolean;
}) {
  const { language, setLanguage, isRead } = useReadingStatus();
  const read = isRead(article.article_key);
  const title = language === 'zh' && article.title_zh ? article.title_zh : article.title;
  const abstract = language === 'zh' ? article.abstract_zh : (article.abstract ?? article.snippet);
  return (
    <div className="reader-article">
      <div className="reader-meta">
        <span className="journal-label">{article.journal.journal_name}</span>
        <span>
          {article.online_published_at === null
            ? 'Online 日期缺失'
            : `Online ${formatDate(article.online_published_at)}`}
        </span>
      </div>
      <h1>{title}</h1>
      {language === 'zh' && article.title_zh ? (
        <p className="reader-original-title">{article.title}</p>
      ) : null}
      <AuthorList
        authors={article.authors}
        authorsText={article.authors_text}
        className="reader-authors"
      />
      <div className="reader-tools">
        <div className="language-switch">
          <button aria-pressed={language === 'zh'} onClick={() => setLanguage('zh')}>
            中文
          </button>
          <button aria-pressed={language === 'en'} onClick={() => setLanguage('en')}>
            原文
          </button>
        </div>
        <FavoriteButton articleKey={article.article_key} />
        <a className="ghost-button" href={article.url} target="_blank" rel="noreferrer">
          出版页面
          <ArrowUpRight size={16} />
        </a>
      </div>
      <section className="reader-abstract">
        <p className="eyebrow">{language === 'zh' ? '中文摘要' : 'ABSTRACT'}</p>
        {abstract ? (
          <p>{abstract}</p>
        ) : (
          <p className="muted">
            {language === 'zh'
              ? '来源未提供可翻译的摘要。'
              : 'The source did not provide an abstract.'}
          </p>
        )}
      </section>
      <div className="reader-citation">
        <span>DOI {article.doi}</span>
        {article.doi ? <CopyButton value={article.doi} /> : null}
      </div>
      <button
        className="primary-button reader-mark"
        onClick={() => onRead(article.article_key, !read)}
      >
        {read ? <Circle size={18} /> : <CheckCheck size={18} />}
        {read ? '设为未读' : readAndNext ? '读完，下一篇' : '标记已读'}
      </button>
      <p className="reader-source-note">中文内容为机器翻译，原文与出版页面可随时对照。</p>
    </div>
  );
}

export function ArticleReader({
  articleId,
  onClose,
  onRead,
  readAndNext,
  previousId,
  nextId,
  onNavigate,
}: {
  articleId: string;
  onClose: () => void;
  onRead: (key: string, read: boolean) => void;
  readAndNext: boolean;
  previousId?: string;
  nextId?: string;
  onNavigate: (id: string) => void;
}) {
  const dialog = useRef<ElementRef<'dialog'>>(null);
  const body = useRef<ElementRef<'div'>>(null);
  const query = useQuery({
    queryKey: ['article', articleId],
    queryFn: () => getArticle(articleId),
    staleTime: Infinity,
  });
  const { isRead, lastChange, undo } = useReadingStatus();
  useEffect(() => {
    const element = dialog.current!;
    element.showModal();
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      element.close();
      document.body.style.overflow = previousOverflow;
    };
  }, []);
  useEffect(() => {
    body.current?.scrollTo({ top: 0 });
  }, [articleId]);
  return (
    <dialog
      ref={dialog}
      className="article-reader"
      aria-label="文献阅读器"
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
      onKeyDown={(event) => {
        if (
          event.ctrlKey ||
          event.metaKey ||
          event.altKey ||
          (event.target as ElementRef<'div'>).closest('input,textarea,select')
        )
          return;
        if (event.key === 'ArrowRight' && nextId) {
          event.preventDefault();
          onNavigate(nextId);
        }
        if (event.key === 'ArrowLeft' && previousId) {
          event.preventDefault();
          onNavigate(previousId);
        }
        if (event.key.toLowerCase() === 'r' && query.data) {
          event.preventDefault();
          onRead(query.data.article_key, !isRead(query.data.article_key));
        }
      }}
    >
      <div className="reader-header">
        <span>专注阅读</span>
        <div>
          <button
            className="icon-button"
            disabled={!previousId}
            onClick={() => previousId && onNavigate(previousId)}
            aria-label="上一篇"
          >
            <ArrowLeft size={18} />
          </button>
          <button
            className="icon-button"
            disabled={!nextId}
            onClick={() => nextId && onNavigate(nextId)}
            aria-label="下一篇"
          >
            <ArrowRight size={18} />
          </button>
          <button className="icon-button" onClick={onClose} aria-label="关闭阅读器">
            <X size={20} />
          </button>
        </div>
      </div>
      <div className="reader-body" ref={body}>
        {query.isLoading ? (
          <LoadingState label="正在加载完整摘要…" />
        ) : query.isError ? (
          <div>
            <ErrorState
              label={query.error instanceof Error ? query.error.message : '文章加载失败'}
            />
            <button className="ghost-button" onClick={() => void query.refetch()}>
              重试
            </button>
          </div>
        ) : query.data ? (
          <ArticleReaderContent article={query.data} onRead={onRead} readAndNext={readAndNext} />
        ) : (
          <EmptyState label="未找到这篇文章" />
        )}
      </div>
      <footer className="reader-keyboard-hint">
        {lastChange ? (
          <button type="button" onClick={undo}>
            撤销刚才的标记
          </button>
        ) : (
          '← / → 切换文章'
        )}
        <span>R 标记已读 · Esc 关闭</span>
      </footer>
    </dialog>
  );
}
