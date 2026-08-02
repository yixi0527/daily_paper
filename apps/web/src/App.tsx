import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { createHashRouter, RouterProvider } from 'react-router-dom';
import { AppShell } from './components/AppShell';
import { FavoritesProvider } from './components/FavoritesProvider';
import { ArticleDetailPage } from './pages/ArticleDetailPage';
import { ArticlesPage } from './pages/ArticlesPage';
import { FavoritesPage } from './pages/FavoritesPage';
import { JournalsPage } from './pages/JournalsPage';
import { NotFoundPage } from './pages/NotFoundPage';
import { SearchPage } from './pages/SearchPage';
import { SyncRunsPage } from './pages/SyncRunsPage';

const queryClient = new QueryClient();

const router = createHashRouter([
  {
    path: '/',
    element: <AppShell />,
    children: [
      { index: true, element: <ArticlesPage /> },
      { path: 'articles', element: <ArticlesPage /> },
      { path: 'articles/:articleId', element: <ArticleDetailPage /> },
      { path: 'favorites', element: <FavoritesPage /> },
      { path: 'search', element: <SearchPage /> },
      { path: 'journals', element: <JournalsPage /> },
      { path: 'sync-runs', element: <SyncRunsPage /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
]);

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <FavoritesProvider>
        <RouterProvider router={router} />
      </FavoritesProvider>
    </QueryClientProvider>
  );
}
