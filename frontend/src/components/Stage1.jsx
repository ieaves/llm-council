import { useEffect, useRef, useState } from 'react';
import Markdown from './Markdown';
import { formatModelName } from '../utils/modelName';
import { copyTextToClipboard } from '../utils/clipboard';
import './Stage1.css';
import './CopyMarkdownButton.css';

export default function Stage1({ responses, totalCount }) {
  const [activeTab, setActiveTab] = useState(0);
  const [copyState, setCopyState] = useState({ status: 'idle', tab: -1 });
  const resetTimerRef = useRef(null);
  const safeResponses = responses || [];
  const responded = safeResponses.length;

  useEffect(() => () => {
    if (resetTimerRef.current) {
      clearTimeout(resetTimerRef.current);
    }
  }, []);

  if (safeResponses.length === 0) {
    return null;
  }

  const activeIndex = Math.min(activeTab, safeResponses.length - 1);
  const activeResponse = safeResponses[activeIndex];
  const activeCopyStatus = copyState.tab === activeIndex ? copyState.status : 'idle';

  const handleCopyMarkdown = async () => {
    const copied = await copyTextToClipboard(activeResponse?.response || '');
    setCopyState({ status: copied ? 'copied' : 'error', tab: activeIndex });
    if (resetTimerRef.current) {
      clearTimeout(resetTimerRef.current);
    }
    resetTimerRef.current = setTimeout(
      () => setCopyState({ status: 'idle', tab: -1 }),
      2000
    );
  };

  return (
    <div className="stage stage1">
      <h3 className="stage-title">Stage 1: Individual Responses</h3>
      <div className="stage-meta">
        <span className="count">
          {responded}
          {totalCount ? ` / ${totalCount}` : ''} responded
        </span>
        {totalCount && responded < totalCount && (
          <span className="pending">Waiting on {totalCount - responded} more...</span>
        )}
      </div>

      <div className="tabs">
        {safeResponses.map((resp, index) => (
          <button
            key={index}
            className={`tab ${activeIndex === index ? 'active' : ''}`}
            onClick={() => setActiveTab(index)}
          >
            {formatModelName(resp.model)}
          </button>
        ))}
      </div>

      <div className="tab-content">
        <div className="response-header">
          <div className="model-name">{formatModelName(activeResponse.model)}</div>
          <button
            type="button"
            className={`copy-markdown-button ${activeCopyStatus}`}
            onClick={handleCopyMarkdown}
            disabled={!activeResponse?.response}
          >
            {activeCopyStatus === 'copied'
              ? 'Copied'
              : activeCopyStatus === 'error'
                ? 'Copy failed'
                : 'Copy Markdown'}
          </button>
        </div>
        <div className="response-text markdown-content">
          <Markdown>{activeResponse.response}</Markdown>
        </div>
      </div>
    </div>
  );
}
