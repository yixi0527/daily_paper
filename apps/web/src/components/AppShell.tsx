import { useState } from 'react';
import { NavLink, Outlet, useLocation, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  BookOpen,
  ChevronDown,
  Heart,
  Menu,
  Newspaper,
  RefreshCw,
  Search,
  Filter,
  X,
  type LucideIcon,
} from 'lucide-react';
import { getJournals } from '../api/client';
import { classNames } from '../lib/utils';

const NAV_ITEMS = [
  { to: '/', label: 'Articles', icon: Newspaper },
  { to: '/favorites', label: 'Favorites', icon: Heart },
  { to: '/search', label: 'Search', icon: Search },
  { to: '/journals', label: 'Journals', icon: BookOpen },
  { to: '/sync-runs', label: 'Sync', icon: RefreshCw },
] satisfies Array<{ to: string; label: string; icon: LucideIcon }>;

export function AppShell() {
  const [navigationOpen, setNavigationOpen] = useState(
    () => !window.matchMedia('(max-width: 680px)').matches,
  );
  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();
  const isArticlesRoute = location.pathname === '/';
  const journalsQuery = useQuery({
    queryKey: ['journals'],
    queryFn: getJournals,
    enabled: isArticlesRoute,
  });
  const journalFilter = searchParams.get('journal') ?? '';
  const authorFilter = searchParams.get('author') ?? '';
  const activeFilterCount = [journalFilter, authorFilter].filter(Boolean).length;

  const updateFilter = (key: 'journal' | 'author', value: string) => {
    const next = new URLSearchParams(searchParams);
    if (value) next.set(key, value);
    else next.delete(key);
    next.set('page', '1');
    setSearchParams(next);
  };

  const clearFilters = () => {
    const next = new URLSearchParams(searchParams);
    next.delete('journal');
    next.delete('author');
    next.delete('page');
    setSearchParams(next);
  };

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand-lockup" aria-label="Daily Paper Tracker">
          <div className="brand-mark" aria-hidden="true">
            <Newspaper size={20} strokeWidth={2.2} />
          </div>
          <div>
            <p className="eyebrow">Daily research digest</p>
            <h1>Daily Paper Tracker</h1>
          </div>
        </div>

        <button
          type="button"
          className="navigation-toggle"
          aria-expanded={navigationOpen}
          aria-controls="primary-navigation"
          onClick={() => setNavigationOpen((open) => !open)}
        >
          <Menu size={17} strokeWidth={2.1} aria-hidden="true" />
          Browse
          <ChevronDown
            size={16}
            strokeWidth={2.1}
            className={classNames('navigation-chevron', navigationOpen && 'open')}
            aria-hidden="true"
          />
        </button>

        <nav
          id="primary-navigation"
          className={classNames('nav-list', !navigationOpen && 'collapsed')}
          aria-label="Primary navigation"
        >
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => classNames('nav-link', isActive && 'active')}
            >
              <item.icon size={17} strokeWidth={2.1} aria-hidden="true" />
              {item.label}
            </NavLink>
          ))}
        </nav>

        {isArticlesRoute && journalsQuery.data ? (
          <div className="topbar-filters" aria-label="Article filters">
            <label className="field">
              <span>Journal</span>
              <select
                value={journalFilter}
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
                value={authorFilter}
                onChange={(event) => updateFilter('author', event.target.value)}
              />
            </label>
            <div className="topbar-filter-actions">
              <span className="mode-pill">
                <Filter size={14} strokeWidth={2.1} aria-hidden="true" />
                {activeFilterCount}
              </span>
              {activeFilterCount ? (
                <button type="button" className="ghost-button" onClick={clearFilters}>
                  <X size={15} strokeWidth={2.2} aria-hidden="true" />
                  Clear
                </button>
              ) : null}
            </div>
          </div>
        ) : null}
      </header>

      <main className="content-shell">
        <Outlet />
      </main>
    </div>
  );
}
