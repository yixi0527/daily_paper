export interface ReadingRecords {
  format: 'daily-paper-reading-records';
  version: 1;
  readKeys: string[];
  favoriteKeys: string[];
  language: 'zh' | 'en';
}

export function parseReadingRecords(text: string): ReadingRecords {
  const data: unknown = JSON.parse(text);
  if (
    typeof data !== 'object' ||
    data === null ||
    !('format' in data) ||
    data.format !== 'daily-paper-reading-records' ||
    !('version' in data) ||
    data.version !== 1
  )
    throw new TypeError('这不是每日文献导出的阅读记录文件。');
  for (const key of ['readKeys', 'favoriteKeys'] as const) {
    const value = (data as Record<string, unknown>)[key];
    if (!Array.isArray(value) || value.some((item: unknown) => typeof item !== 'string'))
      throw new TypeError(`阅读记录中的 ${key} 格式不正确。`);
  }
  if (!('language' in data) || (data.language !== 'zh' && data.language !== 'en'))
    throw new TypeError('阅读语言记录不正确。');
  return data as ReadingRecords;
}
