import { NavLink, Outlet } from 'react-router-dom';
import { BookOpen, Database, Newspaper, RefreshCw, Search, type LucideIcon } from 'lucide-react';
import { classNames } from '../lib/utils';
import { appMode } from '../lib/env';

const NAV_ITEMS = [
  { to: '/', label: 'Articles', icon: Newspaper },
  { to: '/search', label: 'Search', icon: Search },
  { to: '/journals', label: 'Journals', icon: BookOpen },
  { to: '/sync-runs', label: 'Sync', icon: RefreshCw },
] satisfies Array<{ to: string; label: string; icon: LucideIcon }>;

export function AppShell() {
  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand-lockup" aria-label="Daily Paper Tracker">
          <div className="brand-mark" aria-hidden="true">
            <Newspaper size={20} strokeWidth={2.2} />
          </div>
          <div>
            <p className="eyebrow">Beijing 22:00 sync</p>
            <h1>Daily Paper Tracker</h1>
          </div>
        </div>

        <nav className="nav-list">
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

        <div className="mode-pill">
          <Database size={15} strokeWidth={2.1} aria-hidden="true" />
          {appMode === 'static' ? 'GitHub Pages mirror' : 'Live API'}
        </div>
      </header>

      <main className="content-shell">
        <Outlet />
      </main>
    </div>
  );
}
