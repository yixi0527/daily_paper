import { useEffect, useMemo, useState, type ReactNode } from 'react';
import {
  READING_STORAGE_KEY,
  ReadingContext,
  readStoredReadKeys,
  type ReadingStatus,
} from '../hooks/useReadingStatus';

export function ReadingStatusProvider({ children }: { children: ReactNode }) {
  const [readKeys, setReadKeys] = useState(readStoredReadKeys);
  const [language, setLanguage] = useState<'zh' | 'en'>(() => {
    const stored = window.localStorage.getItem('daily-paper:language:v1');
    if (stored === null) return 'zh';
    if (stored !== 'zh' && stored !== 'en') throw new TypeError('阅读语言记录无效');
    return stored;
  });
  const [lastChange, setLastChange] = useState<ReadingStatus['lastChange']>(null);
  useEffect(() => {
    if (lastChange === null) return;
    const timer = window.setTimeout(() => setLastChange(null), 8000);
    return () => window.clearTimeout(timer);
  }, [lastChange]);
  const value = useMemo<ReadingStatus>(() => {
    const readSet = new Set(readKeys);
    const replaceReadKeys = (keys: string[]) => {
      window.localStorage.setItem(READING_STORAGE_KEY, JSON.stringify(keys));
      setReadKeys(keys);
    };
    const setRead = (articleKey: string, read: boolean) => {
      if (readSet.has(articleKey) === read) return;
      replaceReadKeys(
        read ? [...readKeys, articleKey] : readKeys.filter((key) => key !== articleKey),
      );
      setLastChange({ articleKey, previous: readSet.has(articleKey), read });
    };
    return {
      readKeys,
      language,
      lastChange,
      replaceReadKeys,
      setRead,
      isRead: (key) => readSet.has(key),
      toggleRead: (key) => setRead(key, !readSet.has(key)),
      setLanguage: (next) => {
        window.localStorage.setItem('daily-paper:language:v1', next);
        setLanguage(next);
      },
      dismissUndo: () => setLastChange(null),
      undo: () => {
        if (lastChange === null) return;
        replaceReadKeys(
          lastChange.previous
            ? [...new Set([...readKeys, lastChange.articleKey])]
            : readKeys.filter((key) => key !== lastChange.articleKey),
        );
        setLastChange(null);
      },
    };
  }, [readKeys, language, lastChange]);
  return <ReadingContext.Provider value={value}>{children}</ReadingContext.Provider>;
}
