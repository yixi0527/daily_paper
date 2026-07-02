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
        Previous
      </button>
      <span className="pagination-count">
        Page {page} / {totalPages}
      </span>
      <button
        type="button"
        className="pagination-button"
        onClick={() => onPageChange(page + 1)}
        disabled={page >= totalPages}
      >
        Next
        <ChevronRight size={16} strokeWidth={2.2} aria-hidden="true" />
      </button>
    </div>
  );
}
