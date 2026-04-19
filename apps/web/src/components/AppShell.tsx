import { NavLink, Outlet } from 'react-router-dom';
import { classNames } from '../lib/utils';
import { appMode } from '../lib/env';

const NAV_ITEMS = [
  { to: '/', label: 'Dashboard' },
  { to: '/articles', label: 'Articles' },
  { to: '/search', label: 'Search' },
  { to: '/journals', label: 'Journals' },
  { to: '/sync-runs', label: 'Sync Runs' },
];

export function AppShell() {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-block">
          <p className="eyebrow">Daily surveillance</p>
          <h1>Daily Paper Tracker</h1>
          <p className="brand-copy">
            RSS-first monitoring for neuroscience, AI, and flagship multidisciplinary journals.
          </p>
        </div>

        <nav className="nav-list">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => classNames('nav-link', isActive && 'active')}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-footer">
          <p className="eyebrow">Mode</p>
          <div className="mode-pill">{appMode === 'static' ? 'GitHub Pages mirror' : 'Live API'}</div>
        </div>
      </aside>

      <main className="content-shell">
        <Outlet />
      </main>
    </div>
  );
}

