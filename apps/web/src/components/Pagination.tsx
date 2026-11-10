import { ChevronLeft, ChevronRight } from 'lucide-react';

export function Pagination({
  page,
  totalPages,
  onPageChange,
}: {
  page: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}) {
  return (
    <div className="pagination">
      <button
        type="button"
        className="pagination-button"
        onClick={() => onPageChange(page - 1)}
        disabled={page <= 1}
      >
        <ChevronLeft size={16} strokeWidth={2.2} aria-hidden="true" />
        上一页
      </button>
      <span className="pagination-count">
        第 {page} / {totalPages} 页
      </span>
      <button
        type="button"
        className="pagination-button"
        onClick={() => onPageChange(page + 1)}
        disabled={page >= totalPages}
      >
        下一页
        <ChevronRight size={16} strokeWidth={2.2} aria-hidden="true" />
      </button>
    </div>
  );
}
