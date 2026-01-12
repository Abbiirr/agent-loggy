# Frontend Integration Guide - Persistent Conversations

This document outlines all the changes needed for the frontend to integrate with the new persistent conversations API.

---

## Overview

The persistent conversations feature adds a new set of API endpoints that allow the frontend to:
- Create and manage conversation sessions
- Store and retrieve conversation history
- Track analysis pipeline executions
- Support multi-turn conversations with context

---

## API Base URL

All conversation endpoints are under:
```
/api/conversations
```

**Important:** The feature must be enabled on the backend with `USE_PERSISTENT_CONVERSATIONS=true`. If disabled, all endpoints return `501 Not Implemented`.

---

## New API Endpoints

### 1. Create Conversation

**Endpoint:** `POST /api/conversations`

**Request:**
```typescript
interface CreateConversationRequest {
  project?: string;   // e.g., "MMBL", "NCC"
  env?: string;       // e.g., "prod", "staging"
  domain?: string;    // e.g., "NPSB", "BEFTN"
}
```

**Response:** `201 Created`
```typescript
interface ConversationResponse {
  conversation_id: string;      // UUID - use this for all subsequent calls
  project_code: string | null;
  env: string | null;
  domain: string | null;
  title: string | null;
  status: "active" | "archived";
  is_active: boolean;
  message_count: number;
  has_summary: boolean;
  created_at: string;           // ISO 8601 datetime
  updated_at: string;           // ISO 8601 datetime
}
```

**Example:**
```javascript
const response = await fetch('/api/conversations', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    project: 'MMBL',
    env: 'prod',
    domain: 'NPSB'
  })
});
const conversation = await response.json();
// Store conversation.conversation_id for future use
```

---

### 2. List Conversations

**Endpoint:** `GET /api/conversations`

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `project` | string | - | Filter by project code |
| `status` | string | "active" | Filter: "active" or "archived" |
| `limit` | number | 20 | Max results (1-100) |
| `offset` | number | 0 | Pagination offset |

**Response:** `200 OK`
```typescript
interface ConversationListResponse {
  conversations: ConversationResponse[];
  total: number;
  limit: number;
  offset: number;
}
```

**Example:**
```javascript
const response = await fetch('/api/conversations?project=MMBL&status=active&limit=10');
const { conversations, total } = await response.json();
```

---

### 3. Get Conversation Detail

**Endpoint:** `GET /api/conversations/{conversation_id}`

**Response:** `200 OK`
```typescript
interface ConversationDetailResponse extends ConversationResponse {
  messages: MessageResponse[];
  summary: string | null;
  executions: ExecutionResponse[];
}

interface MessageResponse {
  id: number;
  role: "user" | "assistant" | "system";
  content: string;
  message_type: string | null;      // "prompt", "response", "clarification"
  message_metadata: object | null;
  token_count: number | null;
  created_at: string;
}

interface ExecutionResponse {
  execution_id: string;
  status: "pending" | "running" | "completed" | "failed";
  prompt: string;
  extracted_params: object | null;
  trace_ids: string[] | null;
  report_files: string[] | null;
  error_message: string | null;
  started_at: string;
  completed_at: string | null;
}
```

**Example:**
```javascript
const response = await fetch(`/api/conversations/${conversationId}`);
const { messages, executions, summary } = await response.json();
```

---

### 4. Update Conversation

**Endpoint:** `PATCH /api/conversations/{conversation_id}`

**Request:**
```typescript
interface UpdateConversationRequest {
  title?: string;
  domain?: string;
  status?: "active" | "archived";
}
```

**Response:** `200 OK` - Returns updated `ConversationResponse`

**Example:**
```javascript
await fetch(`/api/conversations/${conversationId}`, {
  method: 'PATCH',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ title: 'NPSB Timeout Investigation' })
});
```

---

### 5. Delete (Archive) Conversation

**Endpoint:** `DELETE /api/conversations/{conversation_id}`

**Response:** `200 OK` - Returns archived `ConversationResponse`

**Note:** This performs a soft delete (sets status to "archived"). The conversation can still be retrieved.

**Example:**
```javascript
await fetch(`/api/conversations/${conversationId}`, { method: 'DELETE' });
```

---

### 6. Add Message & Start Analysis

**Endpoint:** `POST /api/conversations/{conversation_id}/messages`

**Request:**
```typescript
interface AddMessageRequest {
  content: string;
  cache?: {
    enabled?: boolean;
    no_cache?: boolean;
    no_store?: boolean;
    ttl_seconds?: number;
  };
}
```

**Response:** `200 OK`
```typescript
interface StreamMessageResponse {
  execution_id: string;
  stream_url: string;   // SSE endpoint for streaming results
}
```

**Example:**
```javascript
const response = await fetch(`/api/conversations/${conversationId}/messages`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ content: 'Show NPSB timeout errors from yesterday' })
});
const { execution_id, stream_url } = await response.json();

// Connect to SSE stream
const eventSource = new EventSource(stream_url);
eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  // Handle streaming events...
};
```

---

### 7. Stream Analysis (SSE)

**Endpoint:** `GET /api/conversations/{conversation_id}/stream/{execution_id}`

**Response:** Server-Sent Events stream

**Events:**
| Event | Description |
|-------|-------------|
| `Extracted Parameters` | Parameters extracted from query |
| `Planned Steps` | Analysis plan |
| `Found relevant files` | Files matching search |
| `Found trace id(s)` | Extracted trace IDs |
| `Compiled Request Traces` | Compiled log entries |
| `Compiled Summary` | Analysis summary |
| `Verification Results` | Relevance verification |
| `error` | Error occurred |
| `done` | Stream complete |

**Example:**
```javascript
function connectToStream(conversationId, executionId) {
  const streamUrl = `/api/conversations/${conversationId}/stream/${executionId}`;
  const eventSource = new EventSource(streamUrl);

  eventSource.addEventListener('Extracted Parameters', (event) => {
    const params = JSON.parse(event.data);
    console.log('Parameters:', params);
  });

  eventSource.addEventListener('Compiled Summary', (event) => {
    const summary = JSON.parse(event.data);
    displaySummary(summary);
  });

  eventSource.addEventListener('done', (event) => {
    const result = JSON.parse(event.data);
    console.log('Complete:', result.status);
    eventSource.close();
    // Refresh messages to get assistant response
    refreshMessages(conversationId);
  });

  eventSource.addEventListener('error', (event) => {
    const error = JSON.parse(event.data);
    console.error('Error:', error);
    eventSource.close();
  });

  return eventSource;
}
```

**Notes:**
- The stream automatically saves the assistant response to the conversation
- After `done` event, refresh messages to see the saved response
- Execution status is updated automatically (`running` → `completed`/`failed`)
- Auto-generates conversation title after first message

---

### 8. Get Messages

**Endpoint:** `GET /api/conversations/{conversation_id}/messages`

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | number | 50 | Max messages (1-100) |
| `offset` | number | 0 | Pagination offset |

**Response:** `200 OK` - Returns `MessageResponse[]`

---

## Frontend Implementation Recommendations

### 1. Conversation State Management

Create a conversation store/context:

```typescript
interface ConversationState {
  currentConversationId: string | null;
  conversations: ConversationResponse[];
  messages: MessageResponse[];
  isLoading: boolean;
  error: string | null;
}

// Actions
type ConversationAction =
  | { type: 'SET_CONVERSATION'; payload: string }
  | { type: 'ADD_MESSAGE'; payload: MessageResponse }
  | { type: 'SET_MESSAGES'; payload: MessageResponse[] }
  | { type: 'UPDATE_EXECUTION'; payload: ExecutionResponse };
```

### 2. Conversation Lifecycle

```typescript
// Start new conversation flow
async function startNewConversation(project: string, env: string, domain: string) {
  // 1. Create conversation
  const conversation = await createConversation({ project, env, domain });

  // 2. Store conversation ID
  setCurrentConversation(conversation.conversation_id);

  return conversation;
}

// Continue existing conversation
async function continueConversation(conversationId: string) {
  // 1. Load conversation with messages
  const detail = await getConversation(conversationId);

  // 2. Restore state
  setMessages(detail.messages);

  return detail;
}
```

### 3. Message Sending with Streaming

```typescript
async function sendMessage(conversationId: string, content: string) {
  // 1. Optimistically add user message to UI
  addMessageToUI({ role: 'user', content, created_at: new Date().toISOString() });

  // 2. Send to API
  const { execution_id, stream_url } = await addMessage(conversationId, { content });

  // 3. Connect to SSE stream
  const eventSource = new EventSource(stream_url);

  // 4. Handle events
  eventSource.addEventListener('message', (event) => {
    const data = JSON.parse(event.data);
    handleStreamEvent(data);
  });

  eventSource.addEventListener('error', () => {
    eventSource.close();
  });

  // 5. Handle completion
  eventSource.addEventListener('done', (event) => {
    eventSource.close();
    // Add assistant response to messages
    refreshMessages(conversationId);
  });
}
```

### 4. Conversation List UI

```tsx
function ConversationList() {
  const [conversations, setConversations] = useState<ConversationResponse[]>([]);
  const [filter, setFilter] = useState({ project: '', status: 'active' });

  useEffect(() => {
    loadConversations();
  }, [filter]);

  async function loadConversations() {
    const { conversations } = await listConversations(filter);
    setConversations(conversations);
  }

  return (
    <div className="conversation-list">
      {conversations.map(conv => (
        <ConversationItem
          key={conv.conversation_id}
          conversation={conv}
          onClick={() => selectConversation(conv.conversation_id)}
        />
      ))}
    </div>
  );
}
```

### 5. Chat Interface Updates

```tsx
function ChatInterface() {
  const { conversationId, messages } = useConversation();

  return (
    <div className="chat-interface">
      {/* Conversation header with title/status */}
      <ConversationHeader conversationId={conversationId} />

      {/* Message history */}
      <MessageList messages={messages} />

      {/* Input with context awareness */}
      <MessageInput
        onSend={(content) => sendMessage(conversationId, content)}
        placeholder={messages.length > 0
          ? "Continue the conversation..."
          : "Start a new analysis..."
        }
      />
    </div>
  );
}
```

---

## UI Components to Add/Modify

### New Components

1. **ConversationList** - Sidebar showing past conversations
2. **ConversationItem** - Single conversation in the list (title, date, status)
3. **ConversationHeader** - Shows current conversation info, title edit, archive button
4. **NewConversationButton** - Starts a new conversation

### Modified Components

1. **ChatInterface** - Add conversation context, load history
2. **MessageInput** - Send to conversation endpoint instead of /chat
3. **MessageList** - Load from conversation messages
4. **ProjectSelector** - Pass project/env/domain when creating conversation

---

## Migration Path

### Phase 1: Parallel Mode
1. Add conversation endpoints alongside existing `/api/chat`
2. Create conversation on first message
3. Store `conversation_id` in session storage

### Phase 2: Conversation-First
1. Show conversation list on app load
2. Require conversation selection before chatting
3. Display message history from selected conversation

### Phase 3: Full Integration
1. Remove legacy `/api/chat` usage
2. Add conversation management UI (rename, archive, search)
3. Add conversation context to all SSE events

---

## Error Handling

### HTTP Status Codes

| Code | Meaning | Frontend Action |
|------|---------|-----------------|
| 200 | Success | Process response |
| 201 | Created | Store new conversation |
| 400 | Bad Request | Show validation error |
| 404 | Not Found | Conversation deleted/invalid |
| 422 | Validation Error | Show field errors |
| 501 | Not Implemented | Feature disabled on backend |
| 500 | Server Error | Show generic error |

### Example Error Handler

```typescript
async function apiCall<T>(fn: () => Promise<T>): Promise<T> {
  try {
    return await fn();
  } catch (error) {
    if (error.status === 501) {
      showError('Conversation history is not enabled. Contact admin.');
    } else if (error.status === 404) {
      showError('Conversation not found. It may have been deleted.');
      clearCurrentConversation();
    } else {
      showError('An error occurred. Please try again.');
    }
    throw error;
  }
}
```

---

## TypeScript Types

Complete type definitions for frontend:

```typescript
// Request types
interface CreateConversationRequest {
  project?: string;
  env?: string;
  domain?: string;
}

interface UpdateConversationRequest {
  title?: string;
  domain?: string;
  status?: 'active' | 'archived';
}

interface AddMessageRequest {
  content: string;
  cache?: CachePolicy;
}

interface CachePolicy {
  enabled?: boolean;
  no_cache?: boolean;
  no_store?: boolean;
  ttl_seconds?: number;
}

// Response types
interface ConversationResponse {
  conversation_id: string;
  project_code: string | null;
  env: string | null;
  domain: string | null;
  title: string | null;
  status: 'active' | 'archived';
  is_active: boolean;
  message_count: number;
  has_summary: boolean;
  created_at: string;
  updated_at: string;
}

interface ConversationDetailResponse extends ConversationResponse {
  messages: MessageResponse[];
  summary: string | null;
  executions: ExecutionResponse[];
}

interface ConversationListResponse {
  conversations: ConversationResponse[];
  total: number;
  limit: number;
  offset: number;
}

interface MessageResponse {
  id: number;
  role: 'user' | 'assistant' | 'system';
  content: string;
  message_type: string | null;
  message_metadata: Record<string, unknown> | null;
  token_count: number | null;
  created_at: string;
}

interface ExecutionResponse {
  execution_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  prompt: string;
  extracted_params: Record<string, unknown> | null;
  trace_ids: string[] | null;
  report_files: string[] | null;
  error_message: string | null;
  started_at: string;
  completed_at: string | null;
}

interface StreamMessageResponse {
  execution_id: string;
  stream_url: string;
}
```

---

## API Client Example

```typescript
class ConversationAPI {
  private baseUrl = '/api/conversations';

  async create(data: CreateConversationRequest): Promise<ConversationResponse> {
    const res = await fetch(this.baseUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    return res.json();
  }

  async list(params?: {
    project?: string;
    status?: string;
    limit?: number;
    offset?: number;
  }): Promise<ConversationListResponse> {
    const query = new URLSearchParams(params as Record<string, string>);
    const res = await fetch(`${this.baseUrl}?${query}`);
    return res.json();
  }

  async get(conversationId: string): Promise<ConversationDetailResponse> {
    const res = await fetch(`${this.baseUrl}/${conversationId}`);
    return res.json();
  }

  async update(
    conversationId: string,
    data: UpdateConversationRequest
  ): Promise<ConversationResponse> {
    const res = await fetch(`${this.baseUrl}/${conversationId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    return res.json();
  }

  async delete(conversationId: string): Promise<ConversationResponse> {
    const res = await fetch(`${this.baseUrl}/${conversationId}`, {
      method: 'DELETE'
    });
    return res.json();
  }

  async addMessage(
    conversationId: string,
    data: AddMessageRequest
  ): Promise<StreamMessageResponse> {
    const res = await fetch(`${this.baseUrl}/${conversationId}/messages`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    return res.json();
  }

  async getMessages(
    conversationId: string,
    params?: { limit?: number; offset?: number }
  ): Promise<MessageResponse[]> {
    const query = new URLSearchParams(params as Record<string, string>);
    const res = await fetch(`${this.baseUrl}/${conversationId}/messages?${query}`);
    return res.json();
  }
}

export const conversationAPI = new ConversationAPI();
```

---

## Checklist for Frontend Implementation

- [ ] Add TypeScript types for all API responses
- [ ] Create `ConversationAPI` client class
- [ ] Add conversation state management (context/store)
- [ ] Create `ConversationList` component
- [ ] Create `ConversationHeader` component
- [ ] Modify `ChatInterface` to use conversation endpoints
- [ ] Modify `MessageInput` to send to conversation
- [ ] Add conversation selection/creation flow
- [ ] Handle 501 error when feature is disabled
- [ ] Add conversation persistence to local storage (optional)
- [ ] Add conversation search/filter UI
- [ ] Add conversation archive/delete functionality
