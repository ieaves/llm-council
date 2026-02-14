import { useEffect, useState } from 'react';
import './CouncilConfigurator.css';

export default function CouncilConfigurator({
  onCreate,
  onCancel,
  defaultModels = [],
  defaultChairman = '',
}) {
  const [modelsText, setModelsText] = useState(defaultModels.join('\n'));
  const [chairman, setChairman] = useState(defaultChairman);

  useEffect(() => {
    setModelsText(defaultModels.join('\n'));
  }, [defaultModels]);

  useEffect(() => {
    setChairman(defaultChairman);
  }, [defaultChairman]);

  const handleSubmit = (e) => {
    e.preventDefault();
    const models = modelsText
      .split('\n')
      .map((m) => m.trim())
      .filter(Boolean);

    onCreate({
      models: models.length ? models : null,
      chairman: chairman?.trim() || null,
    });
  };

  return (
    <div className="council-config-overlay">
      <div className="council-config">
        <h2>Create Conversation</h2>
        <p className="help">
          These fields start with the server config defaults. Edit to add/remove counselors or change the chairman. Leave blank to reuse the defaults.
        </p>

        <form onSubmit={handleSubmit}>
          <label className="field">
            <span>Council models (one per line)</span>
            <textarea
              value={modelsText}
              onChange={(e) => setModelsText(e.target.value)}
              rows={6}
              placeholder="openai/gpt-5.1&#10;ollama/llama3&#10;your-org/custom-model"
            />
            <small className="hint">
              Add any OpenRouter id, or prefix local Ollama models with <code>ollama/&lt;model_name&gt;</code> (e.g., <code>ollama/llama3</code>).
            </small>
          </label>

          <label className="field">
            <span>Chairman model</span>
            <input
              type="text"
              value={chairman}
              onChange={(e) => setChairman(e.target.value)}
              placeholder="google/gemini-3-pro-preview"
            />
            <small className="hint">
              Optional: leave blank to reuse defaults. Can also be a local model using <code>ollama/&lt;name&gt;</code>.
            </small>
          </label>

          <div className="actions">
            <button type="button" className="secondary" onClick={onCancel}>
              Cancel
            </button>
            <button type="submit" className="primary">
              Start Conversation
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
