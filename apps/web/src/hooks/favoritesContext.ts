import { createContext } from 'react';

export const FAVORITES_STORAGE_KEY = 'daily-paper:favorites:v1';

export interface FavoritesContextValue {
  favoriteKeys: string[];
  isFavorite: (articleKey: string) => boolean;
  toggleFavorite: (articleKey: string) => void;
}

export const FavoritesContext = createContext<FavoritesContextValue | null>(null);

export function readStoredFavorites(): string[] {
  const stored = window.localStorage.getItem(FAVORITES_STORAGE_KEY);
  if (stored === null) return [];
  const parsed = JSON.parse(stored) as unknown;
  if (!Array.isArray(parsed) || parsed.some((item) => typeof item !== 'string')) {
    throw new TypeError('Stored favorites must be an array of article keys');
  }
  return parsed;
}
