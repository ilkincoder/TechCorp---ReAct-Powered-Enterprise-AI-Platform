import { createContext, useContext, useState, useCallback, useRef } from 'react'
import { postQueryStream } from '../hooks/useApi'
import { useRole } from './RoleContext'

const QueryContext = createContext(null)

export function QueryProvider({ children }) {
  const { activeRole } = useRole()
  const [isQuerying, setIsQuerying] = useState(false)
  const [lastResult, setLastResult] = useState(null)
  const [latency, setLatency] = useState(null)
  const [error, setError] = useState(null)

  // ── Streaming state ────────────────────────────────────────────────────
  const [streamingContent, setStreamingContent] = useState('')
  const [streamingTool, setStreamingTool] = useState(null)
  const [streamingPhase, setStreamingPhase] = useState(null) // 'planning' | 'executing' | 'generating'
  const [streamingConversationId, setStreamingConversationId] = useState(null)
  const [ambiguity, setAmbiguity] = useState(null) // { originalMessage, field, options }
  const [planSteps, setPlanSteps] = useState([])        // [{tool, goal, status, executionTimeMs, error}]
  const [toolErrors, setToolErrors] = useState([])       // [{tool, message, severity}]
  const [validationWarnings, setValidationWarnings] = useState([])
  const [approvalRequest, setApprovalRequest] = useState(null) // {tool, report_id, title, ...}
  const [reasoningText, setReasoningText] = useState('')
  const [streamingStarted, setStreamingStarted] = useState(false)
  const abortRef = useRef(null)
  const contentRef = useRef('') // Always-current content for callbacks
  const stepTimersRef = useRef({})  // tool → startTime for execution timing

  /**
   * Stream a query via SSE. Returns a promise that resolves with the final result
   * when streaming completes, or null on error.
   */
  const runQueryStream = useCallback((message, conversationId, tool) => {
    // Abort any in-flight stream
    if (abortRef.current) {
      abortRef.current()
      abortRef.current = null
    }

    setIsQuerying(true)
    setError(null)
    setLastResult(null)
    setLatency(null)
    setStreamingContent('')
    setStreamingTool(null)
    setStreamingPhase('planning')
    setStreamingConversationId(conversationId || null)
    setAmbiguity(null)
    setPlanSteps([])
    setToolErrors([])
    setValidationWarnings([])
    setReasoningText('')
    setStreamingStarted(false)
    contentRef.current = ''
    stepTimersRef.current = {}

    return new Promise((resolve) => {
      const start = performance.now()
      let resolved = false
      let finalResult = null
      let pendingApproval = null

      const finish = (result, err) => {
        if (resolved) return
        resolved = true
        setIsQuerying(false)
        setStreamingPhase(null)
        setStreamingTool(null)
        setStreamingConversationId(null)
        // Surface the approval card only after the proposal text has fully
        // streamed — never before/while the model is still describing it.
        if (pendingApproval && !err) {
          setApprovalRequest(pendingApproval)
        }
        if (err) {
          setError(err)
          setLastResult(result) // partial result if any
          resolve(result)
        } else {
          const seconds = (performance.now() - start) / 1000
          setLatency(seconds)
          setLastResult(result)
          setStreamingContent('')
          resolve(result)
        }
      }

      const abort = postQueryStream(message, conversationId, activeRole, tool, {
        onMeta(data) {
          // conversation created — handled by Chat page
          if (data.conversation_id) {
            finalResult = { ...finalResult, conversationId: data.conversation_id }
            setStreamingConversationId(data.conversation_id)
          }
        },

        onPlan(data) {
          setStreamingPhase('executing')
          finalResult = {
            ...finalResult,
            intent: data.intent || '',
            toolsUsed: [],
            sources: [],
            answer: '',
          }
          // Initialize plan steps from structured planner output
          if (data.steps && Array.isArray(data.steps)) {
            setPlanSteps(data.steps.map(s => ({
              tool: s.tool,
              goal: s.goal || '',
              status: 'pending',
              executionTimeMs: null,
              error: '',
            })))
          }
        },

        onPlanStep(data) {
          // A later ReAct turn discovered a new step — append it to the graph
          setPlanSteps(prev => ([
            ...prev,
            {
              tool: data.tool,
              goal: data.goal || '',
              status: 'pending',
              executionTimeMs: null,
              error: '',
            },
          ]))
        },

        onToolStart(data) {
          setStreamingStarted(true)
          setStreamingTool(data.tool)
          const timerKey = data.attempt ? `${data.tool}-retry` : data.tool
          stepTimersRef.current[timerKey] = performance.now()
          if (data.attempt) {
            // Retry attempt — update the retry step and keep the retry progress message
            if (!streamingTool || typeof streamingTool === 'string') {
              setStreamingTool({ tool: data.tool, message: data.message || 'Trying alternative approach' })
            }
            setPlanSteps(prev => {
              const idx = prev.findLastIndex(s =>
                s.tool === data.tool && (s.status === 'retrying' || s.status === 'pending')
              )
              if (idx >= 0) {
                const updated = [...prev]
                updated[idx] = { ...updated[idx], status: 'running', goal: data.message || updated[idx].goal }
                return updated
              }
              return prev
            })
          } else {
            // Original tool execution
            setPlanSteps(prev => prev.map(s =>
              s.tool === data.tool ? { ...s, status: 'running' } : s
            ))
          }
        },

        onToolResult(data) {
          finalResult = {
            ...finalResult,
            toolsUsed: [...(finalResult?.toolsUsed || []), data.tool],
          }
          const timerKey = data.attempt ? `${data.tool}-retry` : data.tool
          const elapsed = stepTimersRef.current[timerKey]
            ? Math.round(performance.now() - stepTimersRef.current[timerKey])
            : null
          if (data.attempt) {
            // Retry result — update the retry step
            setPlanSteps(prev => {
              const idx = prev.findLastIndex(s =>
                s.tool === data.tool && (s.status === 'running' || s.status === 'retrying')
              )
              if (idx >= 0) {
                const updated = [...prev]
                updated[idx] = {
                  ...updated[idx],
                  status: data.success ? 'success' : 'failed',
                  executionTimeMs: elapsed,
                  error: data.summary || '',
                }
                return updated
              }
              return prev
            })
          } else {
            // Original result
            setPlanSteps(prev => prev.map(s =>
              s.tool === data.tool
                ? {
                    ...s,
                    status: data.success ? 'success' : 'failed',
                    executionTimeMs: elapsed,
                    error: data.summary || '',
                  }
                : s
            ))
          }
          // Collect tool errors
          if (!data.success && data.summary) {
            setToolErrors(prev => [...prev, {
              tool: data.tool,
              message: data.summary,
              severity: 'error',
            }])
          }
          if (data.requires_approval) {
            // Stash the approval payload — the card is shown by finish()
            // after the proposal summary has streamed into the chat.
            pendingApproval = {
              tool: data.tool,
              report_id: data.report_id,
              title: data.title || data.summary || '',
              description: data.description || '',
              sections: data.sections || [],
            }
          }
          // Note: streamingTool stays set until first token arrives
          // so the progress indicator doesn't flicker between tool_result and answer
        },

        onDisambiguate(data) {
          setStreamingPhase(null)
          setStreamingTool(null)
          setIsQuerying(false)
          setAmbiguity({
            originalMessage: message,
            conversationId,
            field: data.field,
            options: data.options,
          })
          finish(null, null) // Stop streaming without error
        },

        onToolRetry(data) {
          // Show retry phase in the main chat progress indicator
          setStreamingTool({ tool: data.tool, message: data.message || 'Retrying with different approach' })
          // Add a NEW step entry for the retry attempt — keep the failed one visible
          setPlanSteps(prev => [...prev, {
            tool: data.tool,
            goal: data.message || 'Retrying with different approach',
            status: 'retrying',
            executionTimeMs: null,
            error: '',
          }])
        },

        onToolRetryFailed(data) {
          // Mark the retry step as failed
          setPlanSteps(prev => {
            const idx = prev.findLastIndex(s =>
              s.tool === data.tool && (s.status === 'retrying' || s.status === 'running')
            )
            if (idx >= 0) {
              const updated = [...prev]
              updated[idx] = {
                ...updated[idx],
                status: 'failed',
                error: data.message || 'Retry failed — data not found',
              }
              return updated
            }
            return prev
          })
          setStreamingTool(null)
          if (data.message) {
            setToolErrors(prev => [...prev, {
              tool: data.tool,
              message: data.message,
              severity: 'warning',
            }])
          }
        },

        onToken(data) {
          setStreamingPhase('generating')
          setStreamingTool(null)  // Transition from progress indicator to answer
          contentRef.current += data.text
          setStreamingContent(contentRef.current)
        },

        onSources(data) {
          finalResult = { ...finalResult, sources: data.sources || [] }
        },

        onReasoning(data) {
          setStreamingStarted(true)
          if (data.text) {
            setReasoningText(prev => prev ? prev + '\n\n' + data.text : data.text)
          }
        },

        onValidationError(data) {
          if (data.errors) {
            setValidationWarnings(data.errors)
            setToolErrors(prev => [...prev, ...data.errors.map(e => ({
              tool: 'planner',
              message: e,
              severity: 'error',
            }))])
          }
        },

        onValidationWarning(data) {
          if (data.warnings) {
            setValidationWarnings(prev => [...prev, ...data.warnings])
          }
        },

        onDone(data) {
          const result = {
            ...finalResult,
            intent: data.intent || finalResult?.intent || '',
            toolsUsed: data.tools_used || finalResult?.toolsUsed || [],
            answer: contentRef.current || finalResult?.answer || '',
            conversationId: data.conversation_id || finalResult?.conversationId,
          }
          if (data.conversation_id) {
            setStreamingConversationId(data.conversation_id)
          }
          finish(result, null)
        },

        onError(msg) {
          const result = {
            ...finalResult,
            answer: contentRef.current || finalResult?.answer || '',
          }
          finish(result, msg)
        },
      })

      abortRef.current = abort
    })
  }, [activeRole])

  // Resolve ambiguous name reference with a specific entity
  const resolveAmbiguity = useCallback((option) => {
    if (!ambiguity) return null
    const resolvedMessage =
      `${ambiguity.originalMessage} (specifically ${option.first_name} ${option.last_name}, ${option.job_title}, ID ${option.employee_id})`
    setAmbiguity(null)
    return runQueryStream(resolvedMessage, ambiguity.conversationId)
  }, [ambiguity, runQueryStream])

  // Cleanup on unmount
  const cancelStream = useCallback(() => {
    if (abortRef.current) {
      abortRef.current()
      abortRef.current = null
    }
    setIsQuerying(false)
    setStreamingPhase(null)
    setStreamingTool(null)
  }, [])

  return (
    <QueryContext.Provider value={{
      isQuerying,
      lastResult,
      latency,
      error,
      runQueryStream,
      streamingContent,
      streamingTool,
      streamingPhase,
      streamingConversationId,
      ambiguity,
      resolveAmbiguity,
      cancelStream,
      planSteps,
      toolErrors,
      validationWarnings,
      approvalRequest,
      reasoningText,
      streamingStarted,
      clearApproval: () => setApprovalRequest(null),
    }}>
      {children}
    </QueryContext.Provider>
  )
}

export function useQuery() {
  const ctx = useContext(QueryContext)
  if (!ctx) throw new Error('useQuery must be used within QueryProvider')
  return ctx
}