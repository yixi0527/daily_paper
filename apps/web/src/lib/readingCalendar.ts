import type { ArticleListItem } from '../api/types';

export interface DailyReadingProgress {
  completed: number;
  total: number;
}

const dateFormatter = new Intl.DateTimeFormat('en-US', {
  timeZone: 'Asia/Shanghai',
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
});

export function calendarDateKey(date: Date): string {
  const parts = dateFormatter.formatToParts(date);
  return ['year', 'month', 'day']
    .map((type) => parts.find((part) => part.type === type)!.value)
    .join('-');
}

export function summarizeReadingByAcquiredDate(
  articles: Pick<ArticleListItem, 'article_key' | 'acquired_at'>[],
  isRead: (articleKey: string) => boolean,
) {
  const dailyProgress = new Map<string, DailyReadingProgress>();
  for (const article of articles) {
    const date = calendarDateKey(new Date(article.acquired_at));
    const progress = dailyProgress.get(date) ?? { completed: 0, total: 0 };
    progress.total += 1;
    progress.completed += Number(isRead(article.article_key));
    dailyProgress.set(date, progress);
  }
  return dailyProgress;
}

export function createReadingCalendar(today: Date) {
  const end = new Date(`${calendarDateKey(today)}T12:00:00Z`);
  const start = new Date(end);
  start.setUTCDate(start.getUTCDate() - 364);
  const cursor = new Date(start);
  cursor.setUTCDate(cursor.getUTCDate() - ((cursor.getUTCDay() + 6) % 7));
  const weeks = [];

  while (cursor <= end) {
    const week = [];
    for (let weekday = 0; weekday < 7; weekday += 1) {
      const inRange = cursor >= start && cursor <= end;
      week.push({
        date: cursor.toISOString().slice(0, 10),
        label: cursor.toLocaleDateString('zh-CN', {
          timeZone: 'UTC',
          year: 'numeric',
          month: 'long',
          day: 'numeric',
          weekday: 'long',
        }),
        inRange,
        monthLabel:
          inRange && (cursor.getUTCDate() === 1 || cursor.getTime() === start.getTime())
            ? `${cursor.getUTCMonth() + 1}月`
            : '',
      });
      cursor.setUTCDate(cursor.getUTCDate() + 1);
    }
    weeks.push(week);
  }

  return {
    weeks,
    firstDate: start.toISOString().slice(0, 10),
    lastDate: end.toISOString().slice(0, 10),
  };
}

export function readingColor(ratio: number): string {
  return `hsl(145 45% ${93 - ratio * 61}%)`;
}
