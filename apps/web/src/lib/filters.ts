import type { ArticleDetail, SearchHit } from '../api/types';

export interface ArticleFilterParams {
  page?: number;
  pageSize?: number;
  journal?: string;
  author?: string;
  dateFrom?: string;
  dateTo?: string;
  sourceCategory?: string;
  articleType?: string;
  hasDoi?: string;
  hasAbstract?: string;
}

export interface SearchParams {
  title?: string;
  author?: string;
  abstract?: string;
  journal?: string;
  dateFrom?: string;
  dateTo?: string;
  page?: number;
  pageSize?: number;
}

export function filterArticles(items: ArticleDetail[], params: ArticleFilterParams): ArticleDetail[] {
  return items.filter((item) => {
    if (params.journal && item.journal.slug !== params.journal) return false;
    if (
      params.author &&
      !item.authors.some((author) =>
        author.full_name.toLowerCase().includes(params.author!.toLowerCase()),
      ) &&
      !(item.authors_text ?? '').toLowerCase().includes(params.author.toLowerCase())
    ) {
      return false;
    }
    if (params.sourceCategory && item.source_category !== params.sourceCategory) return false;
    if (params.articleType && item.article_type !== params.articleType) return false;
    if (params.hasDoi === 'true' && !item.doi) return false;
    if (params.hasDoi === 'false' && item.doi) return false;
    if (params.hasAbstract === 'true' && !item.abstract) return false;
    if (params.hasAbstract === 'false' && item.abstract) return false;
    if (params.dateFrom && item.published_at && new Date(item.published_at) < new Date(params.dateFrom)) {
      return false;
    }
    if (params.dateTo && item.published_at && new Date(item.published_at) > new Date(params.dateTo)) {
      return false;
    }
    return true;
  });
}

function highlight(text: string, query: string): string {
  const pattern = new RegExp(query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'ig');
  if (!pattern.test(text)) return text;
  return text.replace(pattern, (match) => `<mark>${match}</mark>`);
}

export function searchArticlesLocally(items: ArticleDetail[], params: SearchParams): SearchHit[] {
  const queryTitle = params.title?.trim().toLowerCase();
  const queryAuthor = params.author?.trim().toLowerCase();
  const queryAbstract = params.abstract?.trim().toLowerCase();
  return items
    .filter((item) => {
      if (params.journal && item.journal.slug !== params.journal) return false;
      if (params.dateFrom && item.published_at && new Date(item.published_at) < new Date(params.dateFrom)) {
        return false;
      }
      if (params.dateTo && item.published_at && new Date(item.published_at) > new Date(params.dateTo)) {
        return false;
      }
      if (queryTitle && !item.title.toLowerCase().includes(queryTitle)) return false;
      if (queryAuthor && !(item.authors_text ?? '').toLowerCase().includes(queryAuthor)) return false;
      if (queryAbstract && !((item.abstract ?? item.snippet ?? '').toLowerCase().includes(queryAbstract))) {
        return false;
      }
      return Boolean(queryTitle || queryAuthor || queryAbstract);
    })
    .map((item) => ({
      article: item,
      score: 100,
      highlights: {
        title: queryTitle ? highlight(item.title, queryTitle) : item.title,
        author: queryAuthor ? highlight(item.authors_text ?? '', queryAuthor) : item.authors_text ?? '',
        abstract: queryAbstract
          ? highlight(item.abstract ?? item.snippet ?? '', queryAbstract)
          : item.abstract ?? item.snippet ?? '',
      },
    }));
}

export function paginate<T>(items: T[], page = 1, pageSize = 20): { items: T[]; total: number } {
  const start = (page - 1) * pageSize;
  return { items: items.slice(start, start + pageSize), total: items.length };
}
