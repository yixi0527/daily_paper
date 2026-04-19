import { useEffect, useState } from 'react';

const KEY = 'daily-paper.recent-searches.v1';

export function useRecentSearches() {
  const [recent, setRecent] = useState<string[]>([]);

  useEffect(() => {
    const raw = localStorage.getItem(KEY);
    if (!raw) return;
    try {
      const parsed = JSON.parse(raw) as string[];
      setRecent(parsed);
    } catch {
      localStorage.removeItem(KEY);
    }
  }, []);

  const remember = (query: string) => {
    if (!query.trim()) return;
    setRecent((current) => {
      const next = [query, ...current.filter((item) => item !== query)].slice(0, 8);
      localStorage.setItem(KEY, JSON.stringify(next));
      return next;
    });
  };

  return { recent, remember };
}

