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

export function compareOnlineDates(
  left: Pick<ArticleListItem, 'online_published_at'>,
  right: Pick<ArticleListItem, 'online_published_at'>,
): number {
  if (left.online_published_at === null) return right.online_published_at === null ? 0 : 1;
  if (right.online_published_at === null) return -1;
  return (
    new Date(right.online_published_at).getTime() - new Date(left.online_published_at).getTime()
  );
}

export function matchesOnlineDateRange(
  article: Pick<ArticleListItem, 'online_published_at'>,
  dateFrom?: string,
  dateTo?: string,
): boolean {
  if (!dateFrom && !dateTo) return true;
  if (article.online_published_at === null) return false;
  const date = calendarDateKey(new Date(article.online_published_at));
  return (!dateFrom || date >= dateFrom) && (!dateTo || date <= dateTo);
}

export function summarizeReadingByOnlineDate(
  articles: Pick<ArticleListItem, 'article_key' | 'online_published_at'>[],
  isRead: (articleKey: string) => boolean,
) {
  const dailyProgress = new Map<string, DailyReadingProgress>();
  let undatedCount = 0;
  for (const article of articles) {
    if (article.online_published_at === null) {
      undatedCount += 1;
      continue;
    }
    const date = calendarDateKey(new Date(article.online_published_at));
    const progress = dailyProgress.get(date) ?? { completed: 0, total: 0 };
    progress.total += 1;
    progress.completed += Number(isRead(article.article_key));
    dailyProgress.set(date, progress);
  }
  return { dailyProgress, undatedCount };
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
