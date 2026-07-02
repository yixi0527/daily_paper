import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useParams } from 'react-router-dom';
import { ExternalLink, Sparkles } from 'lucide-react';
import { generateArticleAnalysis, getArticle } from '../api/client';
import { AuthorList } from '../components/AuthorList';
import { CopyButton } from '../components/CopyButton';
import { EmptyState, ErrorState, LoadingState } from '../components/States';
import { formatDate } from '../lib/utils';
import { isStaticMode } from '../lib/env';

export function ArticleDetailPage() {
  const { articleId = '' } = useParams();
  const queryClient = useQueryClient();
  const articleQuery = useQuery({
    queryKey: ['article', articleId],
    queryFn: () => getArticle(articleId),
  });
  const analysisMutation = useMutation({
    mutationFn: () => generateArticleAnalysis(articleId),
    onSuccess: (updatedArticle) => {
      queryClient.setQueryData(['article', articleId], updatedArticle);
      void queryClient.invalidateQueries({ queryKey: ['articles'] });
      void queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });

  if (articleQuery.isLoading) return <LoadingState label="Loading article detail…" />;
  if (articleQuery.isError) return <ErrorState label="Article detail could not be loaded." />;
  if (!articleQuery.data) return <EmptyState label="Article not found." />;

  const article = articleQuery.data;
  const hasChineseAnalysis = Boolean(
    article.title_zh ||
    article.abstract_zh ||
    article.related_literature_notes_zh?.length ||
    article.heuristic_thoughts_zh?.length,
  );

  return (
    <div className="page-stack">
      <section className="page-header">
        <div>
          <p className="eyebrow">{article.journal.journal_name}</p>
          <h2>{article.title}</h2>
        </div>
        <div className="detail-actions">
          {article.doi ? <CopyButton value={article.doi} /> : null}
          {!isStaticMode ? (
            <button
              type="button"
              className="ghost-button"
              disabled={analysisMutation.isPending}
              onClick={() => analysisMutation.mutate()}
            >
              <Sparkles size={16} strokeWidth={2.2} aria-hidden="true" />
              {analysisMutation.isPending ? '生成中…' : '生成中文解读'}
            </button>
          ) : null}
          <a href={article.url} target="_blank" rel="noreferrer" className="primary-link">
            <ExternalLink size={16} strokeWidth={2.2} aria-hidden="true" />
            Open publisher page
          </a>
        </div>
      </section>
      {analysisMutation.isError ? (
        <section className="state-panel error">
          中文解读生成失败，请检查 LLM 配置和文献库上下文。
        </section>
      ) : null}

      <section className="detail-grid">
        <div className="panel">
          <div className="detail-list">
            <div>
              <span>Authors</span>
              <AuthorList
                authors={article.authors}
                authorsText={article.authors_text}
                className="detail-authors"
              />
            </div>
            <div>
              <span>Published</span>
              <strong>{formatDate(article.published_at)}</strong>
            </div>
            <div>
              <span>DOI</span>
              <strong>{article.doi ?? 'Unavailable'}</strong>
            </div>
            <div>
              <span>Issue / volume</span>
              <strong>
                {article.volume ?? '–'} / {article.issue ?? '–'}
              </strong>
            </div>
            <div>
              <span>Article type</span>
              <strong>{article.article_type ?? 'Unknown'}</strong>
            </div>
            <div>
              <span>Source category</span>
              <strong>{article.source_category}</strong>
            </div>
          </div>
        </div>

        <div className="panel">
          <div className="section-header">
            <div>
              <p className="eyebrow">Abstract</p>
              <h2>Summary metadata</h2>
            </div>
          </div>
          <p className="detail-abstract">
            {article.abstract ?? article.snippet ?? 'No abstract available from source metadata.'}
          </p>
        </div>
      </section>

      <section className="analysis-grid">
        <div className="panel">
          <div className="section-header">
            <div>
              <p className="eyebrow">中文译文</p>
              <h2>Translation</h2>
            </div>
            {article.analysis_generated_at ? (
              <span className="pill muted-pill">{formatDate(article.analysis_generated_at)}</span>
            ) : null}
          </div>
          {hasChineseAnalysis ? (
            <div className="translation-block">
              {article.title_zh ? <h3>{article.title_zh}</h3> : null}
              {article.abstract_zh ? <p>{article.abstract_zh}</p> : null}
            </div>
          ) : (
            <p className="muted">尚未生成中文译文。</p>
          )}
        </div>

        <div className="panel">
          <div className="section-header">
            <div>
              <p className="eyebrow">文献库关联</p>
              <h2>Library links</h2>
            </div>
          </div>
          {article.related_literature_notes_zh?.length ? (
            <ul className="thought-list">
              {article.related_literature_notes_zh.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          ) : (
            <p className="muted">尚未生成文献库关联说明。</p>
          )}
          {article.related_literature?.length ? (
            <div className="related-list">
              {article.related_literature.map((item) => (
                <div key={item.article_id} className="related-item">
                  <strong>{item.title}</strong>
                  <span>
                    {item.journal_name} · {formatDate(item.published_at)} · score{' '}
                    {item.relevance_score.toFixed(2)}
                  </span>
                  {item.shared_terms.length ? <em>{item.shared_terms.join(', ')}</em> : null}
                </div>
              ))}
            </div>
          ) : null}
        </div>

        <div className="panel">
          <div className="section-header">
            <div>
              <p className="eyebrow">启发式思考</p>
              <h2>Heuristics</h2>
            </div>
            {article.analysis_model ? (
              <span className="pill muted-pill">{article.analysis_model}</span>
            ) : null}
          </div>
          {article.heuristic_thoughts_zh?.length ? (
            <ul className="thought-list">
              {article.heuristic_thoughts_zh.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          ) : (
            <p className="muted">尚未生成启发式思考。</p>
          )}
        </div>
      </section>

      {(import.meta.env.DEV || isStaticMode) && article.raw_payload ? (
        <section className="panel">
          <div className="section-header">
            <div>
              <p className="eyebrow">Debug</p>
              <h2>Raw payload</h2>
            </div>
          </div>
          <pre className="code-block">{JSON.stringify(article.raw_payload, null, 2)}</pre>
        </section>
      ) : null}
    </div>
  );
}
