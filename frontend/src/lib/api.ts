import { supabase } from './supabase'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

export interface Message {
  id: string
  conversation_id: string
  user_id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  created_at: string
}

export interface MessagePostResponse {
  user_message: Message
  assistant_message: Message
  run_id: string
}

export interface Conversation {
  id: string
  user_id: string
  title: string
  created_at: string
  updated_at: string
}

export interface ConversationDetail extends Conversation {
  messages: Message[]
}

async function getAuthHeaders(): Promise<HeadersInit> {
  const { data: { session }, error } = await supabase.auth.getSession()
  if (error || !session) {
    throw new Error('Unauthenticated: No active Supabase session found.')
  }
  return {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${session.access_token}`,
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = await getAuthHeaders()
  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      ...headers,
      ...options.headers,
    },
  })

  if (!res.ok) {
    let errorDetail = `HTTP ${res.status} ${res.statusText}`
    try {
      const errorJson = await res.json()
      if (errorJson.detail) {
        errorDetail = typeof errorJson.detail === 'string' ? errorJson.detail : JSON.stringify(errorJson.detail)
      } else if (errorJson.error && errorJson.error.message) {
        errorDetail = errorJson.error.message
      }
    } catch {
      // ignore json parse errors
    }
    throw new Error(errorDetail)
  }

  if (res.status === 204) {
    return undefined as unknown as T
  }

  return res.json() as Promise<T>
}

export async function listConversations(): Promise<Conversation[]> {
  return request<Conversation[]>('/api/v1/conversations')
}

export async function createConversation(title?: string): Promise<Conversation> {
  return request<Conversation>('/api/v1/conversations', {
    method: 'POST',
    body: JSON.stringify({ title: title || 'New Conversation' }),
  })
}

export async function getConversation(id: string): Promise<ConversationDetail> {
  return request<ConversationDetail>(`/api/v1/conversations/${id}`)
}

export async function deleteConversation(id: string): Promise<void> {
  return request<void>(`/api/v1/conversations/${id}`, {
    method: 'DELETE',
  })
}

export async function sendMessage(conversationId: string, content: string): Promise<MessagePostResponse> {
  return request<MessagePostResponse>(`/api/v1/conversations/${conversationId}/messages`, {
    method: 'POST',
    body: JSON.stringify({ content }),
  })
}
