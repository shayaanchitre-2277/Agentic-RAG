import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { App } from '../App'
import { supabase } from '../lib/supabase'

// Mock supabase client
vi.mock('../lib/supabase', () => {
  return {
    supabase: {
      auth: {
        getSession: vi.fn(),
        onAuthStateChange: vi.fn(() => ({
          data: {
            subscription: {
              unsubscribe: vi.fn(),
            },
          },
        })),
        signOut: vi.fn(),
        signInWithPassword: vi.fn(),
        signUp: vi.fn(),
      },
    },
  }
})

// Mock api methods used inside ChatWorkspace
vi.mock('../lib/api', () => {
  return {
    listConversations: vi.fn().mockResolvedValue([
      {
        id: 'conv-123',
        user_id: 'user-456',
        title: 'Investigation Alpha',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    ]),
    getConversation: vi.fn().mockResolvedValue({
      id: 'conv-123',
      user_id: 'user-456',
      title: 'Investigation Alpha',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      messages: [],
    }),
    createConversation: vi.fn(),
    deleteConversation: vi.fn(),
    sendMessage: vi.fn(),
  }
})

describe('App Component Auth State Routing', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders login/signup form when user is unauthenticated', async () => {
    vi.mocked(supabase.auth.getSession).mockResolvedValue({
      data: { session: null },
      error: null,
    })

    render(<App />)

    // Initially displays loading state or renders form after resolution
    await waitFor(() => {
      expect(screen.getByText('Welcome Back')).toBeInTheDocument()
    })

    expect(screen.getByLabelText(/email/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument()
  })

  it('renders ChatWorkspace when user is authenticated', async () => {
    const mockSession = {
      access_token: 'mock-jwt-token',
      token_type: 'bearer',
      user: {
        id: 'user-456',
        email: 'investigator@agency.local',
        app_metadata: {},
        user_metadata: {},
        aud: 'authenticated',
        created_at: new Date().toISOString(),
      },
    }

    vi.mocked(supabase.auth.getSession).mockResolvedValue({
      data: { session: mockSession as any },
      error: null,
    })

    render(<App />)

    await waitFor(() => {
      expect(screen.getByText('investigator@agency.local')).toBeInTheDocument()
    })

    expect(screen.getByRole('button', { name: /\+ new chat/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /sign out/i })).toBeInTheDocument()

    await waitFor(() => {
      expect(screen.getByText('Investigation Alpha')).toBeInTheDocument()
    })
  })
})
