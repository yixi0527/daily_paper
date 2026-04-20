import { Fragment } from 'react';
import { Link } from 'react-router-dom';
import type { Author } from '../api/types';
import { classNames } from '../lib/utils';

function collapseAuthors(authors: Author[]): Array<Author | 'ellipsis'> {
  if (authors.length <= 10) {
    return authors;
  }
  return [...authors.slice(0, 5), 'ellipsis', ...authors.slice(-5)];
}

export function AuthorList({
  authors,
  authorsText,
  className,
}: {
  authors: Author[];
  authorsText?: string | null;
  className?: string;
}) {
  if (!authors.length) {
    return (
      <p className={classNames('author-list', className)}>
        {authorsText ?? 'Author metadata unavailable'}
      </p>
    );
  }

  const displayAuthors = collapseAuthors(authors);

  return (
    <p className={classNames('author-list', className)}>
      {displayAuthors.map((item, index) => (
        <Fragment
          key={item === 'ellipsis' ? `ellipsis-${index}` : `${item.full_name}-${index}`}
        >
          {index > 0 ? <span className="author-separator">, </span> : null}
          {item === 'ellipsis' ? (
            <span className="author-ellipsis">…</span>
          ) : (
            <Link
              className="author-link"
              to={`/articles?author=${encodeURIComponent(item.full_name)}`}
            >
              {item.full_name}
            </Link>
          )}
        </Fragment>
      ))}
    </p>
  );
}
