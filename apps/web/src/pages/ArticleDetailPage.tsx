import { useQuery } from '@tanstack/react-query';
import { Link, useParams } from 'react-router-dom';
import { getArticle } from '../api/client';
import { ArticleReaderContent } from '../components/ArticleReader';
import { LoadingState, ErrorState, EmptyState } from '../components/States';
import { useReadingStatus } from '../hooks/useReadingStatus';

export function ArticleDetailPage() {
  const { articleId = '' } = useParams();
  const { setRead } = useReadingStatus();
  const query = useQuery({
    queryKey: ['article', articleId],
    queryFn: () => getArticle(articleId),
    staleTime: Infinity,
  });
  if (query.isLoading) return <LoadingState label="正在加载文章…" />;
  if (query.isError) return <ErrorState label="文章加载失败，请重新打开。" />;
  if (!query.data) return <EmptyState label="未找到这篇文章" />;
  return (
    <div className="permalink-article">
      <Link className="back-link" to="/articles">
        ← 返回文献库
      </Link>
      <ArticleReaderContent article={query.data} onRead={setRead} />
    </div>
  );
}
