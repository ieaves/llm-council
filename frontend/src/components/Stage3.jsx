import { useEffect, useRef, useState } from 'react';
import Markdown from './Markdown';
import { formatModelName } from '../utils/modelName';
import { copyTextToClipboard } from '../utils/clipboard';
import './Stage3.css';
import './CopyMarkdownButton.css';

export default function Stage3({ finalResponse }) {
  const [copyStatus, setCopyStatus] = useState('idle');
  const resetTimerRef = useRef(null);

  useEffect(() => () => {
    if (resetTimerRef.current) {
      clearTimeout(resetTimerRef.current);
    }
  }, []);

  if (!finalResponse) {
    return null;
  }

  const handleCopyMarkdown = async () => {
    const copied = await copyTextToClipboard(finalResponse.response || '');
    setCopyStatus(copied ? 'copied' : 'error');
    if (resetTimerRef.current) {
      clearTimeout(resetTimerRef.current);
    }
    resetTimerRef.current = setTimeout(() => setCopyStatus('idle'), 2000);
  };

  return (
    <div className="stage stage3">
      <h3 className="stage-title">Stage 3: Final Council Answer</h3>
      <div className="final-response">
        <div className="final-header">
          <div className="chairman-label">
            Chairman: {formatModelName(finalResponse.model)}
          </div>
          <button
            type="button"
            className={`copy-markdown-button ${copyStatus}`}
            onClick={handleCopyMarkdown}
            disabled={!finalResponse.response}
          >
            {copyStatus === 'copied'
              ? 'Copied'
              : copyStatus === 'error'
                ? 'Copy failed'
                : 'Copy Markdown'}
          </button>
        </div>
        <div className="final-text markdown-content">
          <Markdown>{finalResponse.response}</Markdown>
        </div>
      </div>
    </div>
  );
}
