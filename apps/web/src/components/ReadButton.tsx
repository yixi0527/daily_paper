import { Check, Circle } from 'lucide-react';
import { useReadingStatus } from '../hooks/useReadingStatus';
import { classNames } from '../lib/utils';

export function ReadButton({ articleKey }: { articleKey: string }) {
  const { isRead, toggleRead } = useReadingStatus();
  const read = isRead(articleKey);
  const label = read ? '设为未读' : '标记已读';

  return (
    <button
      type="button"
      className={classNames('read-button', read && 'active')}
      aria-pressed={read}
      aria-label={label}
      title={label}
      onClick={() => toggleRead(articleKey)}
    >
      {read ? (
        <Check size={17} strokeWidth={2.2} aria-hidden="true" />
      ) : (
        <Circle size={17} strokeWidth={2} aria-hidden="true" />
      )}
      {read ? '已读' : '标记已读'}
    </button>
  );
}
