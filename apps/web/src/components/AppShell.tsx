import { useState } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import {
  BookOpen,
  ChevronDown,
  Heart,
  Menu,
  Newspaper,
  RefreshCw,
  Search,
  type LucideIcon,
} from 'lucide-react';
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
      </header>

      <main className="content-shell">
        <Outlet />
      </main>
    </div>
  );
}
