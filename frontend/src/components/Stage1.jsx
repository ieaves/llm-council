import { useEffect, useState } from 'react';
import Markdown from './Markdown';
import './Stage1.css';

export default function Stage1({ responses, totalCount }) {
  const [activeTab, setActiveTab] = useState(0);
  const safeResponses = responses || [];
  const responded = safeResponses.length;

  useEffect(() => {
    if (activeTab >= safeResponses.length) {
      setActiveTab(Math.max(0, safeResponses.length - 1));
    }
  }, [safeResponses.length, activeTab]);

  if (safeResponses.length === 0) {
    return null;
  }

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
            className={`tab ${activeTab === index ? 'active' : ''}`}
            onClick={() => setActiveTab(index)}
          >
            {resp.model.split('/')[1] || resp.model}
          </button>
        ))}
      </div>

      <div className="tab-content">
        <div className="model-name">{safeResponses[activeTab].model}</div>
        <div className="response-text markdown-content">
          <Markdown>{safeResponses[activeTab].response}</Markdown>
        </div>
      </div>
    </div>
  );
}
