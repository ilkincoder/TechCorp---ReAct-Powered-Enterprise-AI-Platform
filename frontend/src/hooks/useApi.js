const API_BASE = 'http://localhost:8000';

/**
 * Stream a query via SSE (Server-Sent Events).
 *
 * @param {string} message — user message
 * @param {string|null} conversationId — existing conversation id or null
 * @param {object} callbacks — { onMeta, onPlan, onToolStart, onToolResult, onToken, onSources, onDone, onError }
 * @returns {function} abort — call to cancel the stream
 */
export function postQueryStream(message, conversationId, role, tool, callbacks) {
  const controller = new AbortController();

  fetch(`${API_BASE}/query/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      stream: true,
      session_id: conversationId || null,
      role: role || null,
      tool: tool || null,
    }),
    signal: controller.signal,
  })
    .then(async (response) => {
      if (!response.ok) {
        const detail = await response.json().catch(() => ({}));
        callbacks.onError?.(detail.detail || `Server error: ${response.status}`);
        return;
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        // Keep the last incomplete line in the buffer
        buffer = lines.pop() || '';

        let currentEvent = '';
        let currentData = '';

        for (const line of lines) {
          if (line.startsWith('event: ')) {
            currentEvent = line.slice(7).trim();
          } else if (line.startsWith('data: ')) {
            currentData = line.slice(6);
          } else if (line === '' && currentEvent && currentData) {
            // Empty line = end of event — dispatch
            try {
              const parsed = JSON.parse(currentData);
              switch (currentEvent) {
                case 'meta':
                  callbacks.onMeta?.(parsed);
                  break;
                case 'plan':
                  callbacks.onPlan?.(parsed);
                  break;
                case 'plan_step':
                  callbacks.onPlanStep?.(parsed);
                  break;
                case 'tool_start':
                  callbacks.onToolStart?.(parsed);
                  break;
                case 'tool_result':
                  callbacks.onToolResult?.(parsed);
                  break;
                case 'token':
                  callbacks.onToken?.(parsed);
                  break;
                case 'sources':
                  callbacks.onSources?.(parsed);
                  break;
                case 'done':
                  callbacks.onDone?.(parsed);
                  break;
                case 'disambiguate':
                  callbacks.onDisambiguate?.(parsed);
                  break;
                case 'tool_retry':
                  callbacks.onToolRetry?.(parsed);
                  break;
                case 'tool_retry_failed':
                  callbacks.onToolRetryFailed?.(parsed);
                  break;
                case 'reasoning':
                  callbacks.onReasoning?.(parsed);
                  break;
                case 'validation_error':
                  callbacks.onValidationError?.(parsed);
                  break;
                case 'validation_warning':
                  callbacks.onValidationWarning?.(parsed);
                  break;
                case 'error':
                  callbacks.onError?.(parsed.message || 'Unknown error');
                  break;
              }
            } catch (e) {
              // Skip unparseable events
            }
            currentEvent = '';
            currentData = '';
          }
        }
      }
    })
    .catch((err) => {
      if (err.name !== 'AbortError') {
        callbacks.onError?.(err.message || 'Connection failed');
      }
    });

  return () => controller.abort();
}

// ── Conversations ─────────────────────────────────────────────────────────

export async function fetchConversations() {
  const res = await fetch(`${API_BASE}/conversations`);
  if (!res.ok) throw new Error(`Failed to fetch conversations: ${res.status}`);
  const data = await res.json();
  return data.conversations;
}

export async function createConversation() {
  const res = await fetch(`${API_BASE}/conversations`, { method: 'POST' });
  if (!res.ok) throw new Error(`Failed to create conversation: ${res.status}`);
  return res.json();
}

export async function fetchConversation(id) {
  const res = await fetch(`${API_BASE}/conversations/${id}`);
  if (!res.ok) throw new Error(`Failed to fetch conversation: ${res.status}`);
  return res.json();
}

export async function deleteConversation(id) {
  const res = await fetch(`${API_BASE}/conversations/${id}`, { method: 'DELETE' });
  if (!res.ok) throw new Error(`Failed to delete conversation: ${res.status}`);
  return res.json();
}