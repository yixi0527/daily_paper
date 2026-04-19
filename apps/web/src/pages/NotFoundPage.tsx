import { Link } from 'react-router-dom';

export function NotFoundPage() {
  return (
    <div className="page-stack">
      <section className="panel">
        <p className="eyebrow">404</p>
        <h2>That route does not exist.</h2>
        <Link to="/" className="primary-link">
          Return to dashboard
        </Link>
      </section>
    </div>
  );
}

