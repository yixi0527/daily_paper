import { useRef, useState, type ElementRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Download, Upload, RefreshCw, CheckCircle2, AlertCircle } from 'lucide-react';
import { Link } from 'react-router-dom';
import { getSiteMetadata, getSyncRuns } from '../api/client';
import { useReadingStatus } from '../hooks/useReadingStatus';
import { useFavorites } from '../hooks/useFavorites';
import { parseReadingRecords, type ReadingRecords } from '../lib/readingRecords';
import { formatDateTime } from '../lib/utils';

export function SettingsPage() {
  const metadata = useQuery({ queryKey: ['metadata'], queryFn: getSiteMetadata, staleTime: 60000 });
  const runs = useQuery({ queryKey: ['sync-runs'], queryFn: getSyncRuns });
  const { readKeys, language, replaceReadKeys, setLanguage } = useReadingStatus();
  const { favoriteKeys, replaceFavoriteKeys } = useFavorites();
  const input = useRef<ElementRef<'input'>>(null);
  const [message, setMessage] = useState('');
  const [importError, setImportError] = useState(false);
  const exportRecords = () => {
    const records: ReadingRecords = {
      format: 'daily-paper-reading-records',
      version: 1,
      readKeys,
      favoriteKeys,
      language,
    };
    const url = URL.createObjectURL(
      new window.Blob([JSON.stringify(records, null, 2)], { type: 'application/json' }),
    );
    const link = document.createElement('a');
    link.href = url;
    link.download = 'daily-paper-reading-records.json';
    link.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  };
  const importRecords = async (file: NonNullable<ElementRef<'input'>['files']>[number]) => {
    setMessage('');
    let records: ReadingRecords;
    try {
      records = parseReadingRecords(await file.text());
    } catch (error) {
      if (error instanceof SyntaxError || error instanceof TypeError) {
        setImportError(true);
        setMessage(error.message);
        return;
      }
      throw error;
    }
    replaceReadKeys([...new Set([...readKeys, ...records.readKeys])]);
    replaceFavoriteKeys([...new Set([...favoriteKeys, ...records.favoriteKeys])]);
    setLanguage(records.language);
    setImportError(false);
    setMessage('阅读记录已合并，原有已读和收藏都已保留。');
  };
  const latest = metadata.data;
  return (
    <div className="settings-page">
      <header className="library-heading">
        <div>
          <p className="eyebrow">阅读空间</p>
          <h1>更新与设置</h1>
          <p className="muted">了解数据状态，保管自己的阅读记录。</p>
        </div>
      </header>
      <section className="settings-panel">
        <div className="settings-section-title">
          <CheckCircle2 size={21} />
          <h2>文献更新</h2>
        </div>
        {metadata.isError ? (
          <p role="alert">
            更新状态读取失败：
            {metadata.error instanceof Error ? metadata.error.message : '请求失败'}
          </p>
        ) : latest ? (
          <>
            <dl className="status-facts">
              <div>
                <dt>最近同步</dt>
                <dd>
                  {latest.sync?.finished_at
                    ? formatDateTime(latest.sync.finished_at)
                    : '尚无同步记录'}
                </dd>
              </div>
              <div>
                <dt>文献库</dt>
                <dd>
                  {latest.article_count.toLocaleString('zh-CN')} 篇 · {latest.journal_count} 本期刊
                </dd>
              </div>
              <div>
                <dt>中文翻译</dt>
                <dd>
                  {latest.translations.complete_articles} / {latest.translations.total_articles}{' '}
                  篇已完成
                </dd>
              </div>
            </dl>
            {latest.translations.pending_articles > 0 ? (
              <p className="settings-warning">
                <AlertCircle size={16} />
                {latest.translations.pending_articles} 篇仍待翻译
              </p>
            ) : null}
          </>
        ) : (
          <p>正在读取更新状态…</p>
        )}
        <p className="muted">
          每天 07:30 自动采集与翻译，09:30、12:30 补跑；检查通过后由 Codex
          发布。本机需保持开机并联网。
        </p>
        <button className="ghost-button" onClick={() => window.location.reload()}>
          <RefreshCw size={16} />
          重新加载最新数据
        </button>
      </section>
      <section className="settings-panel">
        <h2>阅读记录</h2>
        <p className="muted">
          已读和收藏保存在当前浏览器。换设备或清理浏览器前，可以先导出；导入时会合并记录。
        </p>
        <div className="record-counts">
          <span>{readKeys.length} 篇已读</span>
          <span>{favoriteKeys.length} 篇收藏</span>
        </div>
        <div className="settings-actions">
          <button className="ghost-button" onClick={exportRecords}>
            <Download size={17} />
            导出阅读记录
          </button>
          <button className="ghost-button" onClick={() => input.current?.click()}>
            <Upload size={17} />
            导入阅读记录
          </button>
          <input
            ref={input}
            type="file"
            accept="application/json,.json"
            className="visually-hidden"
            aria-label="选择阅读记录文件"
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) void importRecords(file);
              event.target.value = '';
            }}
          />
        </div>
        {message ? (
          <p
            className={importError ? 'import-result error' : 'import-result'}
            role={importError ? 'alert' : 'status'}
          >
            {message}
          </p>
        ) : null}
      </section>
      <section className="settings-panel">
        <h2>关于日期与译文</h2>
        <p className="muted">
          列表和阅读日历按 Online 日期组织，日历颜色表示当天文章的已读比例。缺少 Online
          日期的文章仍保留在文献库，可单独筛选；中文译文可与原文和出版页面对照。
        </p>
        <Link className="text-link" to="/journals">
          查看收录期刊 →
        </Link>
      </section>
      {runs.data?.[0] ? (
        <details className="settings-panel">
          <summary>最近一次同步详情</summary>
          <div className="sync-journal-list">
            {runs.data[0].journal_runs.map((run) => (
              <div key={`${run.journal_id}-${run.source_category}`}>
                <span>{run.journal_name}</span>
                <span className={run.status === 'failed' ? 'error-text' : ''}>
                  {run.status === 'success'
                    ? `新增 ${run.inserted_count} 篇`
                    : run.status === 'failed'
                      ? run.error_message
                      : '无新增'}
                </span>
              </div>
            ))}
          </div>
        </details>
      ) : null}
    </div>
  );
}
