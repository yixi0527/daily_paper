import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { createHashRouter, Navigate, RouterProvider } from 'react-router-dom';
import { AppShell } from './components/AppShell';
import { FavoritesProvider } from './components/FavoritesProvider';
import { ReadingStatusProvider } from './components/ReadingStatusProvider';
import { ArticleDetailPage } from './pages/ArticleDetailPage';
import { ArticlesPage } from './pages/ArticlesPage';
import { ReadingErrorBoundary } from './components/ReadingErrorBoundary';
import { JournalsPage } from './pages/JournalsPage';
import { NotFoundPage } from './pages/NotFoundPage';
import { SettingsPage } from './pages/SettingsPage';

const queryClient = new QueryClient();

const router = createHashRouter([
  {
    path: '/',
    element: <AppShell />,
    children: [
      { index: true, element: <Navigate to="/unread" replace /> },
      { path: 'articles', element: <ArticlesPage /> },
      { path: 'read', element: <ArticlesPage readingFilter="read" /> },
      { path: 'unread', element: <ArticlesPage readingFilter="unread" /> },
      { path: 'articles/:articleId', element: <ArticleDetailPage /> },
      { path: 'favorites', element: <ArticlesPage favoritesOnly /> },
      { path: 'search', element: <ArticlesPage /> },
      { path: 'journals', element: <JournalsPage /> },
      { path: 'settings', element: <SettingsPage /> },
      { path: 'sync-runs', element: <SettingsPage /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
]);

export function App() {
  return (
    <ReadingErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <FavoritesProvider>
          <ReadingStatusProvider>
            <RouterProvider router={router} />
          </ReadingStatusProvider>
        </FavoritesProvider>
      </QueryClientProvider>
    </ReadingErrorBoundary>
  );
}
