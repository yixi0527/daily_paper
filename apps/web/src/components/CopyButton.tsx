import { useState } from 'react';
import { Check, Copy } from 'lucide-react';

export function CopyButton({ value }: { value: string }) {
  const [copied, setCopied] = useState(false);

  return (
    <button
      type="button"
      className="ghost-button"
      onClick={async () => {
        await navigator.clipboard.writeText(value);
        setCopied(true);
        window.setTimeout(() => setCopied(false), 1200);
      }}
    >
      {copied ? (
        <Check size={16} strokeWidth={2.2} aria-hidden="true" />
      ) : (
        <Copy size={16} strokeWidth={2.2} aria-hidden="true" />
      )}
      {copied ? 'Copied' : 'Copy DOI'}
    </button>
  );
}
