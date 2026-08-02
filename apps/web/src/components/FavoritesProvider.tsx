import { useMemo, useState, type ReactNode } from 'react';
import {
  FAVORITES_STORAGE_KEY,
  FavoritesContext,
  readStoredFavorites,
  type FavoritesContextValue,
} from '../hooks/favoritesContext';

export function FavoritesProvider({ children }: { children: ReactNode }) {
  const [favoriteKeys, setFavoriteKeys] = useState(readStoredFavorites);

  const value = useMemo<FavoritesContextValue>(() => {
    const favoriteSet = new Set(favoriteKeys);
    return {
      favoriteKeys,
      isFavorite: (articleKey) => favoriteSet.has(articleKey),
      toggleFavorite: (articleKey) => {
        const next = favoriteSet.has(articleKey)
          ? favoriteKeys.filter((key) => key !== articleKey)
          : [...favoriteKeys, articleKey];
        window.localStorage.setItem(FAVORITES_STORAGE_KEY, JSON.stringify(next));
        setFavoriteKeys(next);
      },
    };
  }, [favoriteKeys]);

  return <FavoritesContext.Provider value={value}>{children}</FavoritesContext.Provider>;
}
