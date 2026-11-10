import { Check, ChevronRight } from 'lucide-react';
import { Link } from 'react-router-dom';

export function ReadingProgress({
  completed,
  total,
  filtered,
  readOnly,
  search,
}: {
  completed: number;
  total: number;
  filtered: boolean;
  readOnly: boolean;
  search: string;
}) {
  const percentage = total === 0 ? 0 : (completed / total) * 100;
  const percentageLabel = percentage.toLocaleString('zh-CN', { maximumFractionDigits: 1 });

  return (
    <section className="reading-overview" aria-label="阅读进度">
      <div className="reading-progress-heading">
        <div className="reading-progress-label">
          <span className="reading-progress-icon" aria-hidden="true">
            <Check size={18} />
          </span>
          <div>
            <p className="eyebrow">阅读进度</p>
            <p className="reading-progress-count" aria-live="polite" aria-atomic="true">
              <strong>{completed.toLocaleString('zh-CN')}</strong>
              <span> / {total.toLocaleString('zh-CN')} 篇已读</span>
            </p>
          </div>
        </div>
        <span className="reading-progress-percentage">{percentageLabel}%</span>
      </div>
      <progress
        className="reading-progress-bar"
        value={completed}
        max={total || 1}
        aria-label="文章阅读进度"
        aria-valuetext={`${completed} / ${total} 篇已读，${percentageLabel}%`}
      />
      <div className="reading-progress-footer">
        <span>
          {filtered ? '当前筛选范围' : '全部文章'} · {total - completed} 篇未读
        </span>
        <Link to={{ pathname: readOnly ? '/' : '/read', search }}>
          {readOnly ? '查看全部' : '查看已读'}
          <ChevronRight size={15} aria-hidden="true" />
        </Link>
      </div>
    </section>
  );
}
