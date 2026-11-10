import { useMemo, useState, type ReactNode } from 'react';
import {
  READING_STORAGE_KEY,
  ReadingContext,
  readStoredReadKeys,
  type ReadingStatus,
} from '../hooks/useReadingStatus';

export function ReadingStatusProvider({ children }: { children: ReactNode }) {
  const [readKeys, setReadKeys] = useState(readStoredReadKeys);
  const value = useMemo<ReadingStatus>(() => {
    const readSet = new Set(readKeys);
    return {
      isRead: (articleKey) => readSet.has(articleKey),
      toggleRead: (articleKey) => {
        const next = readSet.has(articleKey)
          ? readKeys.filter((key) => key !== articleKey)
          : [...readKeys, articleKey];
        window.localStorage.setItem(READING_STORAGE_KEY, JSON.stringify(next));
        setReadKeys(next);
      },
    };
  }, [readKeys]);

  return <ReadingContext.Provider value={value}>{children}</ReadingContext.Provider>;
}
