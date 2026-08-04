import { buildQuery } from '../lib/utils';
import { apiBaseUrl, isStaticMode, staticDataBase } from '../lib/env';
import {
  type ArticleDetail,
  type ArticleListItem,
  type ArticleListResponse,
  type DashboardData,
  type Journal,
  type SearchResponse,
  type SiteDataBundle,
  type SyncRun,
} from './types';
import {
  filterArticles,
  paginate,
  searchArticlesLocally,
  type ArticleFilterParams,
  type SearchParams,
} from '../lib/filters';

let siteDataPromise: Promise<SiteDataBundle> | null = null;

async function loadSiteData(): Promise<SiteDataBundle> {
  if (!siteDataPromise) {
    siteDataPromise = fetch(`${staticDataBase}/site-data.json`).then((response) => {
      if (!response.ok) throw new Error('Failed to load static data bundle');
      return response.json() as Promise<SiteDataBundle>;
    });
  }
  return siteDataPromise;
}

async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export async function getDashboard(): Promise<DashboardData> {
  if (isStaticMode) {
    const bundle = await loadSiteData();
    return bundle.dashboard;
  }
  return apiGet<DashboardData>('/dashboard');
}

export async function getJournals(): Promise<Journal[]> {
  if (isStaticMode) {
    const bundle = await loadSiteData();
    return bundle.journals;
  }
  return apiGet<Journal[]>('/journals');
}

export async function getJournal(slug: string): Promise<Journal | undefined> {
  const journals = await getJournals();
  return journals.find((item) => item.slug === slug);
}

export async function listArticles(params: ArticleFilterParams): Promise<ArticleListResponse> {
  if (isStaticMode) {
    const bundle = await loadSiteData();
    const filtered = filterArticles(bundle.articles, params).sort((a, b) => {
      return new Date(b.display_date).getTime() - new Date(a.display_date).getTime();
    });
    const page = params.page ?? 1;
    const pageSize = params.pageSize ?? 20;
    const paged = paginate(filtered, page, pageSize);
    return {
      items: paged.items,
      meta: {
        page,
        page_size: pageSize,
        total: paged.total,
        total_pages: Math.max(1, Math.ceil(paged.total / pageSize)),
      },
    };
  }
  return apiGet<ArticleListResponse>(
    `/articles${buildQuery({
      page: params.page ?? 1,
      page_size: params.pageSize ?? 20,
      journal: params.journal,
      author: params.author,
      date_from: params.dateFrom,
      date_to: params.dateTo,
      source_category: params.sourceCategory,
      article_type: params.articleType,
      has_doi: params.hasDoi,
      has_abstract: params.hasAbstract,
    })}`,
  );
}

export async function getArticle(articleId: string): Promise<ArticleDetail | undefined> {
  if (isStaticMode) {
    const bundle = await loadSiteData();
    return bundle.articles.find((item) => item.id === articleId);
  }
  return apiGet<ArticleDetail>(`/articles/${articleId}`);
}

export async function searchArticles(params: SearchParams): Promise<SearchResponse> {
  if (isStaticMode) {
    const bundle = await loadSiteData();
    const hits = searchArticlesLocally(bundle.articles, params);
    const page = params.page ?? 1;
    const pageSize = params.pageSize ?? 20;
    const paged = paginate(hits, page, pageSize);
    return {
      items: paged.items,
      meta: {
        page,
        page_size: pageSize,
        total: paged.total,
        total_pages: Math.max(1, Math.ceil(paged.total / pageSize)),
      },
    };
  }
  return apiGet<SearchResponse>(
    `/search${buildQuery({
      title: params.title,
      author: params.author,
      abstract: params.abstract,
      journal: params.journal,
      date_from: params.dateFrom,
      date_to: params.dateTo,
      page: params.page ?? 1,
      page_size: params.pageSize ?? 20,
    })}`,
  );
}

export async function getFavoriteArticles(articleKeys: string[]): Promise<ArticleListItem[]> {
  if (!articleKeys.length) return [];
  const requestedKeys = new Set(articleKeys);
  if (isStaticMode) {
    const bundle = await loadSiteData();
    return bundle.articles
      .filter((article) => requestedKeys.has(article.article_key))
      .sort((a, b) => new Date(b.display_date).getTime() - new Date(a.display_date).getTime());
  }

  const firstPage = await listArticles({ page: 1, pageSize: 100 });
  const remainingPages = Array.from(
    { length: Math.max(0, firstPage.meta.total_pages - 1) },
    (_, index) => index + 2,
  );
  const remainingResponses = await Promise.all(
    remainingPages.map((page) => listArticles({ page, pageSize: 100 })),
  );
  return [firstPage, ...remainingResponses]
    .flatMap((response) => response.items)
    .filter((article) => requestedKeys.has(article.article_key));
}

export async function getSyncRuns(): Promise<SyncRun[]> {
  if (isStaticMode) {
    const bundle = await loadSiteData();
    return bundle.sync_runs;
  }
  return apiGet<SyncRun[]>('/sync/runs');
}

export async function runSync(): Promise<SyncRun> {
  return apiPost<SyncRun>('/sync/run', { triggered_by: 'web' });
}

export async function runJournalSync(slug: string): Promise<SyncRun> {
  return apiPost<SyncRun>(`/sync/run/${slug}`, { triggered_by: 'web' });
}
