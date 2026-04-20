export interface SourceState {
  source_category: string;
  source_name: string;
  source_url: string | null;
  last_status_code: number | null;
  last_checked_at: string | null;
  last_success_at: string | null;
  latest_seen_published_at: string | null;
  last_error: string | null;
  consecutive_failures: number;
}

export interface Journal {
  id: number;
  journal_id: string;
  slug: string;
  journal_name: string;
  publisher: string;
  issn_print: string | null;
  issn_online: string | null;
  homepage_url: string;
  enabled: boolean;
  polling_strategy: string;
  primary_source: string | null;
  fallback_source: string | null;
  source_states?: SourceState[];
}

export interface Author {
  position: number;
  given_name: string | null;
  family_name: string | null;
  full_name: string;
  affiliation: string | null;
}

export interface ArticleListItem {
  id: string;
  title: string;
  doi: string | null;
  url: string;
  abstract: string | null;
  snippet: string | null;
  source_category: string;
  article_type: string | null;
  volume: string | null;
  issue: string | null;
  published_at: string | null;
  online_published_at: string | null;
  print_published_at: string | null;
  first_author: string | null;
  authors_text: string | null;
  authors: Author[];
  journal: Journal;
}

export interface ArticleDetail extends ArticleListItem {
  pages: string | null;
  article_number: string | null;
  source_name: string;
  source_uid: string | null;
  extra_metadata: Record<string, unknown> | null;
  raw_payload: Record<string, unknown> | null;
}

export interface PaginationMeta {
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

export interface ArticleListResponse {
  items: ArticleListItem[];
  meta: PaginationMeta;
}

export interface SearchHit {
  article: ArticleListItem;
  highlights: Record<string, string>;
  score: number;
}

export interface SearchResponse {
  items: SearchHit[];
  meta: PaginationMeta;
}

export interface JournalCount {
  journal_slug: string;
  journal_name: string;
  count: number;
}

export interface DashboardData {
  today_new_articles: number;
  last_sync_status: string | null;
  trend: Array<{ date: string; count: number }>;
  by_journal: JournalCount[];
  latest_articles: ArticleListItem[];
}

export interface SyncRunJournal {
  journal_id: number;
  source_category: string;
  source_name: string | null;
  status: string;
  attempts: number;
  fetched_count: number;
  inserted_count: number;
  updated_count: number;
  failed_count: number;
  skipped_count: number;
  error_message: string | null;
  started_at: string;
  finished_at: string | null;
  duration_ms: number | null;
}

export interface SyncRun {
  id: string;
  triggered_by: string;
  scope: string;
  requested_journal_slug: string | null;
  requested_category: string | null;
  status: string;
  total_journals: number;
  total_processed: number;
  total_fetched: number;
  total_inserted: number;
  total_updated: number;
  total_failed: number;
  notes: string | null;
  started_at: string;
  finished_at: string | null;
  journal_runs: SyncRunJournal[];
}

export interface SiteDataBundle {
  journals: Journal[];
  articles: ArticleDetail[];
  dashboard: DashboardData;
  sync_runs: SyncRun[];
}
