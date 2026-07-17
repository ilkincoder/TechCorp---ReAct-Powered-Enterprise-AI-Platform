import { useState, useEffect, useRef, useCallback } from 'react'
import { useQuery } from '../context/QueryContext'
import { fetchConversation } from '../hooks/useApi'
import MessageBubble from '../components/MessageBubble'
import ChatInput from '../components/ChatInput'
import LoadingSpinner from '../components/LoadingSpinner'
import ConversationList from '../components/ConversationList'
import './Chat.css'

export default function Chat() {
  const {
    isQuerying,
    error,
    runQueryStream,
    streamingContent,
    streamingTool,
    streamingPhase,
    streamingConversationId,
    ambiguity,
    resolveAmbiguity,
    toolErrors,
    planSteps,
    approvalRequest,
    reasoningText,
    streamingStarted,
    clearApproval,
  } = useQuery()

  const [messages, setMessages] = useState([])
  const [conversationId, setConversationId] = useState(null)
  const [loadingHistory, setLoadingHistory] = useState(false)
  const [convRefreshKey, setConvRefreshKey] = useState(0)
  const [prefillText, setPrefillText] = useState('')
  const messagesEnd = useRef(null)
  const skipHistoryLoad = useRef(false) // skip load when conv auto-created during streaming

  // Auto-scroll when messages change or streaming content updates
  useEffect(() => {
    messagesEnd.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamingContent, isQuerying])

  // Load conversation history when switching conversations
  useEffect(() => {
    if (!conversationId) {
      setMessages([])
      return
    }

    // Skip loading when conversation was just auto-created by streaming
    // (messages are already in state from the streaming flow)
    if (skipHistoryLoad.current) {
      skipHistoryLoad.current = false
      return
    }

    let cancelled = false
    setLoadingHistory(true)

    fetchConversation(conversationId)
      .then((conv) => {
        if (cancelled) return
        setMessages(
          conv.messages.map((m) => ({
            role: m.role,
            content: m.content,
            sources: m.sources,
            toolsUsed: m.tools_used,
            intent: m.intent,
          }))
        )
      })
      .catch(() => {
        if (!cancelled) setMessages([])
      })
      .finally(() => {
        if (!cancelled) setLoadingHistory(false)
      })

    return () => { cancelled = true }
  }, [conversationId])

  // Adopt the conversation id as soon as the backend auto-creates it (meta
  // event) — otherwise isStreamingHere goes false mid-stream and all live
  // streaming UI (reasoning, plan, spinner) disappears for new conversations.
  useEffect(() => {
    if (!conversationId && isQuerying && streamingConversationId) {
      skipHistoryLoad.current = true
      setConversationId(streamingConversationId)
      setConvRefreshKey(k => k + 1)
    }
  }, [streamingConversationId, isQuerying, conversationId])

  // ── Send message ──────────────────────────────────────────────────────

  async function handleSend(message, tool) {
    // Add user message immediately
    const userMsg = { role: 'user', content: message }
    setMessages((prev) => [...prev, userMsg])

    // Use existing conversation or let backend create one
    const result = await runQueryStream(message, conversationId, tool)

    if (result) {
      // If backend created a new conversation, update our id
      if (result.conversationId && !conversationId) {
        skipHistoryLoad.current = true
        setConversationId(result.conversationId)
        setConvRefreshKey(k => k + 1)
      }

      // Add assistant message
      const assistantMsg = {
        role: 'assistant',
        content: result.answer,
        sources: result.sources,
        toolsUsed: result.toolsUsed,
        intent: result.intent,
      }
      setMessages((prev) => [...prev, assistantMsg])
    }
  }

  // ── Disambiguation handler ─────────────────────────────────────────────

  async function handleResolveAmbiguity(option) {
    const result = await resolveAmbiguity(option)
    if (result) {
      if (result.conversationId && !conversationId) {
        skipHistoryLoad.current = true
        setConversationId(result.conversationId)
        setConvRefreshKey(k => k + 1)
      }
      setMessages((prev) => [...prev, {
        role: 'assistant',
        content: result.answer,
        sources: result.sources,
        toolsUsed: result.toolsUsed,
        intent: result.intent,
      }])
    }
  }

  // ── Conversation management ────────────────────────────────────────────

  const handleSelectConversation = useCallback((id) => {
    setConversationId(id)
  }, [])

  const handleNewConversation = useCallback((id) => {
    if (id) {
      setConversationId(id)
    } else {
      setConversationId(null)
      setMessages([])
    }
  }, [])

  // Only show streaming UI when the active conversation owns the stream.
  // null streamingConversationId means no stream is active (or pre-creation).
  const isStreamingHere =
    streamingConversationId === null || streamingConversationId === conversationId

  // ── Approval handler ────────────────────────────────────────────────────

  async function handleApproveReport() {
    if (!approvalRequest) return
    const plan = {
      report_id: approvalRequest.report_id,
      title: approvalRequest.title,
      sections: approvalRequest.sections,
      description: approvalRequest.description,
    }
    clearApproval()
    // Send as a user message that generates the report
    const msg = `Generate report #${plan.report_id}: ${plan.title}`
    await handleSend(msg)
  }

  function handleRejectReport() {
    clearApproval()
    // Invite the user to re-describe the report — their next message flows
    // through the normal propose path.
    setMessages((prev) => [...prev, {
      role: 'assistant',
      content: "Report proposal declined. Describe the exact report you'd like — sections, data, focus areas — and I'll propose a new plan.",
      sources: [],
      toolsUsed: [],
      intent: '',
    }])
  }

  // ── Streaming message object (shown while AI is responding) ────────────

  const streamingMessage =
    isStreamingHere && isQuerying && streamingStarted
      ? {
          role: 'assistant',
          content: streamingContent,
          sources: [],
          toolsUsed: [],
          intent: '',
        }
      : null

  // ── Render ────────────────────────────────────────────────────────────

  const showWelcome = messages.length === 0 && !isQuerying && !loadingHistory

  return (
    <div className="chat-page">
      <ConversationList
        activeId={conversationId}
        onSelect={handleSelectConversation}
        onNew={handleNewConversation}
        refreshKey={convRefreshKey}
      />

      <div className="chat-main">
        <header className="chat-header">
          <div className="chat-header-info">
            <h2 className="chat-title">AI Chat</h2>
            <span className="chat-subtitle">
              {conversationId ? `${messages.length} messages` : 'New conversation'}
            </span>
          </div>
        </header>

        <div className="messages-area">
          {loadingHistory && (
            <div className="loading-history">Loading conversation…</div>
          )}

          {showWelcome && (
            <div className="welcome">
              <h2>TechCorp AI</h2>
              <p>
                Ask me anything about your enterprise. I can search the knowledge
                base, query databases, run Python, search the web, and more.
              </p>
              <div className="suggestions">
                <button onClick={() => setPrefillText('What tools do you have available?')}>
                  What tools are available?
                </button>
                <button onClick={() => setPrefillText('Search the knowledge base for onboarding policies.')}>
                  Search onboarding policies
                </button>
                <button onClick={() => setPrefillText('How many employees are in the database?')}>
                  Query employee count
                </button>
              </div>
            </div>
          )}

          {messages.map((msg, i) => (
            <MessageBubble key={i} message={msg} />
          ))}

          {/* Streaming message — shows while AI is generating */}
          {streamingMessage && (
            <MessageBubble
              message={streamingMessage}
              isStreaming={streamingPhase === 'generating'}
              streamingTool={streamingTool}
              toolErrors={toolErrors}
              reasoningText={reasoningText}
            />
          )}

          {/* Show spinner only during planning phase (no tokens yet) and only in the streaming conversation */}
          {isStreamingHere && isQuerying && !streamingMessage && (
            <LoadingSpinner />
          )}

          {error && (
            <div className="error-banner">
              ⚠ {error}
            </div>
          )}

          <div ref={messagesEnd} />
        </div>

        {ambiguity && (
          <div className="disambiguate-bar">
            <p className="disambiguate-label">
              Multiple matches for "{ambiguity.options[0]?.first_name || ambiguity.field}" — which one?
            </p>
            <div className="disambiguate-chips">
              {ambiguity.options.map((opt) => (
                <button
                  key={opt.employee_id}
                  className="disambiguate-chip"
                  onClick={() => handleResolveAmbiguity(opt)}
                >
                  <strong>{opt.first_name} {opt.last_name}</strong>
                  <span className="chip-role">{opt.job_title}</span>
                  <span className="chip-dept">{opt.department_name}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {approvalRequest && (
          <div className="approval-bar">
            <p className="approval-label">
              Generate report: <strong>{approvalRequest.title}</strong>?
            </p>
            {approvalRequest.description && (
              <p className="approval-desc">{approvalRequest.description}</p>
            )}
            {approvalRequest.sections?.length > 0 && (
              <div className="approval-sections">
                Sections: {approvalRequest.sections.join(' → ')}
              </div>
            )}
            <div className="approval-buttons">
              <button className="approval-approve" onClick={handleApproveReport}>
                ✓ Approve
              </button>
              <button className="approval-reject" onClick={handleRejectReport}>
                ✗ Reject
              </button>
            </div>
          </div>
        )}

        <ChatInput
          onSend={handleSend}
          disabled={isQuerying}
          prefill={prefillText}
          onPrefillConsumed={() => setPrefillText('')}
        />
      </div>
    </div>
  )
}
