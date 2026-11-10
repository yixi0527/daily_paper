import { useQuery } from '@tanstack/react-query';
import { NavLink, Outlet, useLocation } from 'react-router-dom';
import { BookOpen, CheckCheck, Circle, Heart, Library, Settings2, Undo2, X } from 'lucide-react';
import { getAllArticles, getSiteMetadata } from '../api/client';
import { useReadingStatus } from '../hooks/useReadingStatus';
import { useFavorites } from '../hooks/useFavorites';
import { formatDateTime } from '../lib/utils';

const sections = [
  { to: '/unread', label: '未读', icon: Circle, key: 'unread' },
  { to: '/articles', label: '全部文章', icon: Library, key: 'all' },
  { to: '/read', label: '已读', icon: CheckCheck, key: 'read' },
  { to: '/favorites', label: '收藏', icon: Heart, key: 'favorites' },
] as const;

export function AppShell() {
  const library = useQuery({
    queryKey: ['library'],
    queryFn: () => getAllArticles(),
    staleTime: 60000,
  });
  const metadata = useQuery({ queryKey: ['metadata'], queryFn: getSiteMetadata, staleTime: 60000 });
  const { isRead, language, setLanguage, lastChange, undo, dismissUndo } = useReadingStatus();
  const { isFavorite } = useFavorites();
  const location = useLocation();
  const counts = library.data
    ? {
        all: library.data.length,
        read: library.data.filter((article) => isRead(article.article_key)).length,
        unread: library.data.filter((article) => !isRead(article.article_key)).length,
        favorites: library.data.filter((article) => isFavorite(article.article_key)).length,
      }
    : null;
  const navSearch = new URLSearchParams(location.search);
  navSearch.delete('page');
  navSearch.delete('article');

  return (
    <div className="app-shell">
      <a
        className="skip-link"
        href="#main-content"
        onClick={(event) => {
          event.preventDefault();
          document.getElementById('main-content')?.focus();
        }}
      >
        跳到文章列表
      </a>
      <aside className="workspace-sidebar">
        <NavLink to="/unread" className="brand-lockup">
          <span className="brand-mark">
            <BookOpen size={22} />
          </span>
          <span>
            <strong>每日文献</strong>
            <small>DAILY PAPER</small>
          </span>
        </NavLink>
        <p className="sidebar-caption">你的阅读空间</p>
        <nav className="workspace-nav" aria-label="文献分类">
          {sections.map((item) => (
            <NavLink
              key={item.key}
              to={{ pathname: item.to, search: navSearch.toString() }}
              className={({ isActive }) => `workspace-nav-link${isActive ? ' active' : ''}`}
            >
              <item.icon size={18} aria-hidden="true" />
              <span>{item.label}</span>
              <small>{counts ? counts[item.key].toLocaleString('zh-CN') : '…'}</small>
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="sidebar-note">
            <span className="status-dot" />
            <span>每天，为好问题留一点时间。</span>
          </div>
          <NavLink to="/settings" className="sidebar-settings">
            <Settings2 size={17} />
            更新状态与设置
          </NavLink>
          <p className="sidebar-update">
            {metadata.data?.sync?.finished_at
              ? `数据更新于 ${formatDateTime(metadata.data.sync.finished_at)}`
              : metadata.isError
                ? '更新状态暂不可用'
                : '正在读取更新状态…'}
          </p>
        </div>
      </aside>
      <div className="workspace-main">
        <header className="workspace-topbar">
          <span className="mobile-brand">每日文献</span>
          <span className="desktop-workspace-title">文献阅读工作台</span>
          <div className="language-switch" aria-label="阅读语言">
            <button
              type="button"
              aria-pressed={language === 'zh'}
              onClick={() => setLanguage('zh')}
            >
              中文
            </button>
            <button
              type="button"
              aria-pressed={language === 'en'}
              onClick={() => setLanguage('en')}
            >
              原文
            </button>
          </div>
          <NavLink to="/settings" className="mobile-settings" aria-label="设置">
            <Settings2 size={19} />
          </NavLink>
        </header>
        <main id="main-content" className="content-shell" tabIndex={-1}>
          <Outlet />
        </main>
      </div>
      {lastChange ? (
        <div className="reading-toast" role="status">
          <CheckCheck size={18} />
          <span>{lastChange.read ? '已标记为已读' : '已设为未读'}</span>
          <button type="button" onClick={undo}>
            <Undo2 size={15} />
            撤销
          </button>
          <button type="button" className="icon-button" aria-label="关闭提示" onClick={dismissUndo}>
            <X size={16} />
          </button>
        </div>
      ) : null}
    </div>
  );
}
