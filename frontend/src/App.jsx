import { useState, useEffect, useRef } from 'react';
import Sidebar from './components/Sidebar';
import ChatInterface from './components/ChatInterface';
import CouncilConfigurator from './components/CouncilConfigurator';
import { api } from './api';
import './App.css';

const DEBUG_EVENTS = import.meta.env.VITE_DEBUG_EVENTS === 'true';

function App() {
  const [conversations, setConversations] = useState([]);
  const [currentConversationId, setCurrentConversationId] = useState(null);
  const [currentConversation, setCurrentConversation] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [defaultModels, setDefaultModels] = useState([]);
  const [defaultChairman, setDefaultChairman] = useState('');
  const [showConfigurator, setShowConfigurator] = useState(false);
  const [configuratorKey, setConfiguratorKey] = useState(0);
  const abortControllerRef = useRef(null);

  // Load conversations on mount
  useEffect(() => {
    loadConversations();
    loadModels();
  }, []);

  // Load conversation details when selected
  useEffect(() => {
    if (currentConversationId) {
      loadConversation(currentConversationId);
    }
  }, [currentConversationId]);

  const loadConversations = async () => {
    try {
      const convs = await api.listConversations();
      setConversations(convs);
    } catch (error) {
      console.error('Failed to load conversations:', error);
    }
  };

  const loadModels = async () => {
    try {
      const models = await api.listModels();
      setDefaultModels(models.council_models || []);
      setDefaultChairman(models.chairman_model || '');
      return models;
    } catch (error) {
      console.error('Failed to load models:', error);
      return null;
    }
  };

  const loadConversation = async (id) => {
    try {
      const conv = await api.getConversation(id);
      setCurrentConversation(conv);
    } catch (error) {
      console.error('Failed to load conversation:', error);
    }
  };

  const handleNewConversation = async () => {
    // Ensure defaults are loaded before showing the configurator
    await loadModels();
    setConfiguratorKey((k) => k + 1); // force fresh state each open
    setShowConfigurator(true);
  };

  const handleSelectConversation = (id) => {
    setCurrentConversationId(id);
  };

  const handleSendMessage = async (content) => {
    if (!currentConversationId) return;

    setIsLoading(true);
    try {
      // Optimistically add user message to UI
      const userMessage = { role: 'user', content };
      setCurrentConversation((prev) => ({
        ...prev,
        messages: [...prev.messages, userMessage],
      }));

      // Create a partial assistant message that will be updated progressively
      const assistantMessage = {
        role: 'assistant',
        stage1: [],
        stage2: [],
        stage3: null,
        metadata: null,
        loading: {
          stage1: false,
          stage2: false,
          stage3: false,
        },
      };

      // Add the partial assistant message
      setCurrentConversation((prev) => ({
        ...prev,
        messages: [...prev.messages, assistantMessage],
      }));

      // Send message with streaming
      const controller = new AbortController();
      abortControllerRef.current = controller;

      await api.sendMessageStream(
        currentConversationId,
        content,
        (eventType, event) => {
          if (DEBUG_EVENTS) {
            // Helpful debugging in the browser console
            // eslint-disable-next-line no-console
            console.log('[sse]', eventType, event);
          }
          switch (eventType) {
            case 'stage1_start':
              setCurrentConversation((prev) => {
                const messages = [...prev.messages];
                const lastMsg = messages[messages.length - 1];
                lastMsg.loading.stage1 = true;
                return { ...prev, messages };
              });
              break;

          case 'stage1_progress':
            setCurrentConversation((prev) => {
              const messages = [...prev.messages];
              const lastMsg = messages[messages.length - 1];
              const existing = lastMsg.stage1 || [];
              const filtered = existing.filter((resp) => resp.model !== event.model);
              if (event.response !== undefined) {
                filtered.push({
                  model: event.model,
                  response: event.response || '',
                });
              }
              lastMsg.stage1 = filtered;
              return { ...prev, messages };
            });
            break;

          case 'stage1_complete':
            setCurrentConversation((prev) => {
              const messages = [...prev.messages];
              const lastMsg = messages[messages.length - 1];
              lastMsg.stage1 = event.data;
              lastMsg.loading.stage1 = false;
              return { ...prev, messages };
            });
            break;

          case 'stage2_start':
            setCurrentConversation((prev) => {
              const messages = [...prev.messages];
              const lastMsg = messages[messages.length - 1];
              lastMsg.loading.stage2 = true;
              return { ...prev, messages };
            });
            break;

          case 'stage2_progress':
            setCurrentConversation((prev) => {
              const messages = [...prev.messages];
              const lastMsg = messages[messages.length - 1];
              const existing = lastMsg.stage2 || [];
              const filtered = existing.filter((resp) => resp.model !== event.model);
              if (event.ranking !== undefined) {
                filtered.push({
                  model: event.model,
                  ranking: event.ranking || '',
                  parsed_ranking: null,
                });
              }
              lastMsg.stage2 = filtered;
              return { ...prev, messages };
            });
            break;

          case 'stage2_complete':
            setCurrentConversation((prev) => {
              const messages = [...prev.messages];
              const lastMsg = messages[messages.length - 1];
              lastMsg.stage2 = event.data;
              lastMsg.metadata = event.metadata;
              lastMsg.loading.stage2 = false;
              return { ...prev, messages };
            });
            break;

          case 'stage3_start':
            setCurrentConversation((prev) => {
              const messages = [...prev.messages];
              const lastMsg = messages[messages.length - 1];
              lastMsg.loading.stage3 = true;
              return { ...prev, messages };
            });
            break;

          case 'stage3_complete':
            setCurrentConversation((prev) => {
              const messages = [...prev.messages];
              const lastMsg = messages[messages.length - 1];
              lastMsg.stage3 = event.data;
              lastMsg.loading.stage3 = false;
              return { ...prev, messages };
            });
            break;

          case 'title_complete':
            // Reload conversations to get updated title
            loadConversations();
            break;

          case 'complete':
            // Stream complete, reload conversations list
            loadConversations();
            setIsLoading(false);
            break;

          case 'error':
            console.error('Stream error:', event.message);
            setIsLoading(false);
            break;

          default:
            console.log('Unknown event type:', eventType);
          }
        },
        controller.signal
      );

      abortControllerRef.current = null;
    } catch (error) {
      if (error.name === 'AbortError') {
        console.warn('Council run aborted by user');
        setIsLoading(false);
      } else {
        console.error('Failed to send message:', error);
        // Remove optimistic messages on error
        setCurrentConversation((prev) => ({
          ...prev,
          messages: prev.messages.slice(0, -2),
        }));
        setIsLoading(false);
      }
    }
  };

  const handleStop = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsLoading(false);
    // Remove the in-flight assistant placeholder
    setCurrentConversation((prev) => {
      if (!prev || !prev.messages || prev.messages.length === 0) return prev;
      const messages = [...prev.messages];
      const last = messages[messages.length - 1];
      if (last?.role === 'assistant' && last.loading) {
        const hasData = last.stage1 || last.stage2 || last.stage3;
        if (hasData) {
          last.loading = {
            stage1: false,
            stage2: false,
            stage3: false,
          };
          messages[messages.length - 1] = last;
        } else {
          messages.pop();
        }
      }
      return { ...prev, messages };
    });
  };

  return (
    <div className="app">
      <Sidebar
        conversations={conversations}
        currentConversationId={currentConversationId}
        onSelectConversation={handleSelectConversation}
        onNewConversation={handleNewConversation}
      />
      {showConfigurator && (
        <CouncilConfigurator
          key={configuratorKey}
          defaultModels={defaultModels}
          defaultChairman={defaultChairman}
          onCancel={() => setShowConfigurator(false)}
          onCreate={async ({ models, chairman }) => {
            try {
              const newConv = await api.createConversation(models, chairman);
              setConversations((prev) => [
                {
                  id: newConv.id,
                  created_at: newConv.created_at,
                  title: newConv.title,
                  message_count: 0,
                  council_models: newConv.council_models,
                  chairman_model: newConv.chairman_model,
                },
                ...prev,
              ]);
              setCurrentConversationId(newConv.id);
            } catch (error) {
              console.error('Failed to create conversation:', error);
            } finally {
              setShowConfigurator(false);
            }
          }}
        />
      )}
      <ChatInterface
        conversation={currentConversation}
        onSendMessage={handleSendMessage}
        isLoading={isLoading}
        onStop={handleStop}
      />
    </div>
  );
}

export default App;
