import { createContext, useContext } from 'react';

export const READING_STORAGE_KEY = 'daily-paper:read-articles:v1';

export interface ReadingStatus {
  isRead: (articleKey: string) => boolean;
  toggleRead: (articleKey: string) => void;
}

export const ReadingContext = createContext<ReadingStatus | null>(null);

export function readStoredReadKeys(): string[] {
  const stored = window.localStorage.getItem(READING_STORAGE_KEY);
  if (stored === null) return [];
  const parsed: unknown = JSON.parse(stored);
  if (!Array.isArray(parsed) || parsed.some((key) => typeof key !== 'string')) {
    throw new TypeError('Stored reading status must be an array of article keys');
  }
  return parsed;
}

export function useReadingStatus() {
  const context = useContext(ReadingContext);
  if (context === null) throw new Error('useReadingStatus requires ReadingStatusProvider');
  return context;
}
