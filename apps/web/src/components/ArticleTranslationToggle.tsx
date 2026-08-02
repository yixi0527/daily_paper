import { useId, useState } from 'react';
import { ChevronDown, Languages } from 'lucide-react';

type ArticleTranslationToggleProps = {
  titleZh: string | null;
  abstractZh: string | null;
  variant: 'card' | 'detail';
};

export function ArticleTranslationToggle({
  titleZh,
  abstractZh,
  variant,
}: ArticleTranslationToggleProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const regionId = useId();
  const hasTranslation = Boolean(titleZh || abstractZh);

  if (!hasTranslation) return null;

  return (
    <div className={`translation-disclosure translation-disclosure-${variant}`}>
      <button
        type="button"
        className="translation-toggle"
        aria-expanded={isExpanded}
        aria-controls={regionId}
        onClick={() => setIsExpanded((current) => !current)}
      >
        <Languages size={16} strokeWidth={2.1} aria-hidden="true" />
        <span>{isExpanded ? '隐藏中文翻译' : '显示中文翻译'}</span>
        <ChevronDown
          size={16}
          strokeWidth={2.1}
          aria-hidden="true"
          className={isExpanded ? 'translation-chevron expanded' : 'translation-chevron'}
        />
      </button>

      {isExpanded ? (
        <div id={regionId} className="translation-content">
          {titleZh ? (
            <div className="translation-section">
              <p className="translation-section-label">中文标题</p>
              <p className="translation-title">{titleZh}</p>
            </div>
          ) : null}
          {abstractZh ? (
            <div className="translation-section">
              <p className="translation-section-label">中文摘要</p>
              <p className="article-snippet article-snippet-zh">{abstractZh}</p>
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
