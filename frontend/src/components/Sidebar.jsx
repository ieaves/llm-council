import './Sidebar.css';

export default function Sidebar({
  conversations,
  currentConversationId,
  onSelectConversation,
  onNewConversation,
}) {
  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <div className="brand">
          <img src="/logo.png" alt="LLM Council logo" className="brand-logo" />
          <span className="brand-name">LLM Council</span>
        </div>
        <button
          className="new-conversation-btn"
          onClick={onNewConversation}
          title="Start a new conversation"
        >
          + New Conversation
        </button>
      </div>

      <div className="conversation-list">
        {conversations.length === 0 ? (
          <div className="no-conversations">No conversations yet</div>
        ) : (
          conversations.map((conv) => (
            <div
              key={conv.id}
              className={`conversation-item ${
                conv.id === currentConversationId ? 'active' : ''
              }`}
              onClick={() => onSelectConversation(conv.id)}
            >
              <div className="conversation-title">
                {conv.title || 'New Conversation'}
              </div>
              <div className="conversation-meta">
                {conv.message_count} messages
              </div>
              {(conv.council_models || conv.chairman_model) && (
                <div className="conversation-council">
                  {conv.chairman_model && (
                    <span className="chair-label">
                      Chair: {conv.chairman_model.split('/')[1] || conv.chairman_model}
                    </span>
                  )}
                  {conv.council_models && conv.council_models.length > 0 && (
                    <span className="council-label">
                      Council: {conv.council_models.slice(0, 3).map((m) => m.split('/')[1] || m).join(', ')}
                      {conv.council_models.length > 3 ? ` +${conv.council_models.length - 3}` : ''}
                    </span>
                  )}
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
