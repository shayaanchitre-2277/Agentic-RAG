import React, { useEffect, useState, useRef } from 'react'
import {
  listConversations,
  createConversation,
  getConversation,
  deleteConversation,
  sendMessage,
  type Conversation,
  type Message,
} from '../../lib/api'

interface ChatWorkspaceProps {
  userEmail: string
  onSignOut: () => void
}

export const ChatWorkspace: React.FC<ChatWorkspaceProps> = ({ userEmail, onSignOut }) => {
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [loadingConversations, setLoadingConversations] = useState(false)
  const [loadingMessages, setLoadingMessages] = useState(false)
  const [sending, setSending] = useState(false)
  const [inputContent, setInputContent] = useState('')
  const [error, setError] = useState<string | null>(null)

  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    if (typeof messagesEndRef.current?.scrollIntoView === 'function') {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, sending])

  const fetchConversations = async () => {
    setLoadingConversations(true)
    setError(null)
    try {
      const data = await listConversations()
      setConversations(data)
      if (data.length > 0 && !activeConversationId) {
        setActiveConversationId(data[0].id)
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load conversations.')
    } finally {
      setLoadingConversations(false)
    }
  }

  useEffect(() => {
    fetchConversations()
  }, [])

  useEffect(() => {
    if (!activeConversationId) {
      setMessages([])
      return
    }

    const fetchDetail = async () => {
      setLoadingMessages(true)
      setError(null)
      try {
        const detail = await getConversation(activeConversationId)
        setMessages(detail.messages || [])
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : 'Failed to load messages.')
      } finally {
        setLoadingMessages(false)
      }
    }

    fetchDetail()
  }, [activeConversationId])

  const handleNewChat = async () => {
    setError(null)
    try {
      const newConv = await createConversation('New Investigation')
      setConversations((prev) => [newConv, ...prev])
      setActiveConversationId(newConv.id)
      setMessages([])
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to create new conversation.')
    }
  }

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation()
    if (!confirm('Are you sure you want to delete this conversation?')) {
      return
    }

    try {
      await deleteConversation(id)
      setConversations((prev) => prev.filter((c) => c.id !== id))
      if (activeConversationId === id) {
        const remaining = conversations.filter((c) => c.id !== id)
        setActiveConversationId(remaining.length > 0 ? remaining[0].id : null)
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to delete conversation.')
    }
  }

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault()
    const content = inputContent.trim()
    if (!content || sending) return

    setError(null)
    setInputContent('')
    setSending(true)

    try {
      let convId = activeConversationId
      if (!convId) {
        const newConv = await createConversation(content.slice(0, 30))
        setConversations((prev) => [newConv, ...prev])
        setActiveConversationId(newConv.id)
        convId = newConv.id
      }

      // Optimistically add user placeholder
      const tempUserMsg: Message = {
        id: 'temp-' + Date.now(),
        conversation_id: convId,
        user_id: 'temp-user',
        role: 'user',
        content,
        created_at: new Date().toISOString(),
      }
      setMessages((prev) => [...prev, tempUserMsg])

      const res = await sendMessage(convId, content)
      // Replace temp with actual server user and assistant messages
      setMessages((prev) => [
        ...prev.filter((m) => m.id !== tempUserMsg.id),
        res.user_message,
        res.assistant_message,
      ])
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to generate assistant response.')
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="chat-container">
      {/* Sidebar */}
      <aside className="chat-sidebar">
        <div className="sidebar-header">
          <div className="user-profile">
            <div className="user-avatar" title={userEmail}>
              {userEmail.charAt(0).toUpperCase()}
            </div>
            <div className="user-info">
              <span className="user-email" title={userEmail}>
                {userEmail}
              </span>
              <span className="user-status">Online (Local)</span>
            </div>
          </div>
          <button className="btn btn-secondary btn-sm" onClick={onSignOut}>
            Sign Out
          </button>
        </div>

        <div className="sidebar-action">
          <button className="btn btn-primary btn-block" onClick={handleNewChat}>
            + New Chat
          </button>
        </div>

        <div className="conversation-list" role="navigation" aria-label="Conversations">
          {loadingConversations ? (
            <div className="empty-state">Loading chats...</div>
          ) : conversations.length === 0 ? (
            <div className="empty-state">No conversations yet.<br />Start a new investigation!</div>
          ) : (
            conversations.map((conv) => (
              <div
                key={conv.id}
                className={`conversation-item ${conv.id === activeConversationId ? 'active' : ''}`}
                onClick={() => setActiveConversationId(conv.id)}
              >
                <span className="conversation-title" title={conv.title}>
                  {conv.title}
                </span>
                <button
                  className="btn-delete"
                  title="Delete chat"
                  aria-label="Delete conversation"
                  onClick={(e) => handleDelete(conv.id, e)}
                >
                  &times;
                </button>
              </div>
            ))
          )}
        </div>
      </aside>

      {/* Main Chat Panel */}
      <main className="chat-main">
        {error && (
          <div className="alert alert-error chat-alert" role="alert">
            <span>{error}</span>
            <button className="alert-close" onClick={() => setError(null)}>&times;</button>
          </div>
        )}

        <div className="messages-area">
          {!activeConversationId ? (
            <div className="chat-welcome">
              <h2>Agentic RAG Assistant</h2>
              <p>Select a conversation from the sidebar or click <strong>+ New Chat</strong> to start.</p>
            </div>
          ) : loadingMessages ? (
            <div className="empty-state">Loading conversation history...</div>
          ) : messages.length === 0 ? (
            <div className="chat-welcome">
              <h3>Empty Investigation</h3>
              <p>Type your query below to consult the walking skeleton assistant.</p>
            </div>
          ) : (
            messages.map((msg) => (
              <div
                key={msg.id}
                className={`message-row ${msg.role === 'user' ? 'message-user' : 'message-assistant'}`}
              >
                <div className="message-bubble">
                  <div className="message-sender">
                    {msg.role === 'user' ? 'You' : 'Assistant'}
                  </div>
                  <div className="message-content">{msg.content}</div>
                </div>
              </div>
            ))
          )}

          {sending && (
            <div className="message-row message-assistant">
              <div className="message-bubble message-loading">
                <div className="message-sender">Assistant</div>
                <div className="typing-indicator">
                  <span></span><span></span><span></span>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Message Input Form */}
        <form onSubmit={handleSend} className="message-composer">
          <input
            type="text"
            placeholder="Ask a question or enter an investigation query..."
            value={inputContent}
            onChange={(e) => setInputContent(e.target.value)}
            disabled={sending}
            aria-label="Message text"
          />
          <button type="submit" className="btn btn-primary" disabled={sending || !inputContent.trim()}>
            {sending ? 'Thinking...' : 'Send'}
          </button>
        </form>
      </main>
    </div>
  )
}
