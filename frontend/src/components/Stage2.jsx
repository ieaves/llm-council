import { useState } from 'react';
import Markdown from './Markdown';
import { formatModelName } from '../utils/modelName';
import './Stage2.css';

function deAnonymizeText(text, labelToModel) {
  if (!labelToModel) return text;

  let result = text;
  // Replace each "Response X" with the actual model name
  Object.entries(labelToModel).forEach(([label, model]) => {
    result = result.replace(new RegExp(label, 'g'), `**${formatModelName(model)}**`);
  });
  return result;
}

export default function Stage2({ rankings, labelToModel, aggregateRankings, totalCount }) {
  const [activeTab, setActiveTab] = useState(0);
  const safeRankings = rankings || [];
  const responded = safeRankings.length;

  if (safeRankings.length === 0) {
    return null;
  }

  const activeIndex = Math.min(activeTab, safeRankings.length - 1);

  return (
    <div className="stage stage2">
      <h3 className="stage-title">Stage 2: Peer Rankings</h3>
      <div className="stage-meta">
        <span className="count">
          {responded}
          {totalCount ? ` / ${totalCount}` : ''} evaluations in
        </span>
        {totalCount && responded < totalCount && (
          <span className="pending">Waiting on {totalCount - responded} more...</span>
        )}
      </div>

      <h4>Raw Evaluations</h4>
      <p className="stage-description">
        Each model evaluated all responses (anonymized as Response A, B, C, etc.) and provided rankings.
        Below, model names are shown in <strong>bold</strong> for readability, but the original evaluation used anonymous labels.
      </p>

      <div className="tabs">
        {safeRankings.map((rank, index) => (
          <button
            key={index}
            className={`tab ${activeIndex === index ? 'active' : ''}`}
            onClick={() => setActiveTab(index)}
          >
            {formatModelName(rank.model)}
          </button>
        ))}
      </div>

      <div className="tab-content">
        <div className="ranking-model">
          {formatModelName(safeRankings[activeIndex].model)}
        </div>
        <div className="ranking-content markdown-content">
          <Markdown>
            {deAnonymizeText(safeRankings[activeIndex].ranking, labelToModel)}
          </Markdown>
        </div>

        {safeRankings[activeIndex].parsed_ranking &&
         safeRankings[activeIndex].parsed_ranking.length > 0 && (
          <div className="parsed-ranking">
            <strong>Extracted Ranking:</strong>
            <ol>
              {safeRankings[activeIndex].parsed_ranking.map((label, i) => (
                <li key={i}>
                  {labelToModel && labelToModel[label]
                    ? formatModelName(labelToModel[label])
                    : label}
                </li>
              ))}
            </ol>
          </div>
        )}
      </div>

      {aggregateRankings && aggregateRankings.length > 0 && (
        <div className="aggregate-rankings">
          <h4>Aggregate Rankings (Street Cred)</h4>
          <p className="stage-description">
            Combined results across all peer evaluations (lower score is better):
          </p>
          <div className="aggregate-list">
            {aggregateRankings.map((agg, index) => (
              <div key={index} className="aggregate-item">
                <span className="rank-position">#{index + 1}</span>
                <span className="rank-model">
                  {formatModelName(agg.model)}
                </span>
                <span className="rank-score">
                  Avg: {agg.average_rank.toFixed(2)}
                </span>
                <span className="rank-count">
                  ({agg.rankings_count} votes)
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
