import { Component, type ReactNode } from 'react';

export class ReadingErrorBoundary extends Component<
  { children: ReactNode },
  { error: Error | null }
> {
  state: { error: Error | null } = { error: null };
  static getDerivedStateFromError(error: Error) {
    return { error };
  }
  render() {
    if (this.state.error)
      return (
        <main className="fatal-error">
          <h1>阅读空间暂时无法打开</h1>
          <p>{this.state.error.message}</p>
          <p>本地记录已保留。刷新后仍有问题时，请保留这条错误信息。</p>
          <button className="primary-button" onClick={() => window.location.reload()}>
            重新加载
          </button>
        </main>
      );
    return this.props.children;
  }
}
