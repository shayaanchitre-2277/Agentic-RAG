import React, { useEffect, useState } from 'react'
import type { Session } from '@supabase/supabase-js'
import { supabase } from './lib/supabase'
import { AuthForm } from './components/AuthForm'
import { ChatWorkspace } from './features/chat/ChatWorkspace'
import './App.css'

export const App: React.FC = () => {
  const [session, setSession] = useState<Session | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Initial session retrieval
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session)
      setLoading(false)
    })

    // Listen to auth changes
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session)
      setLoading(false)
    })

    return () => {
      subscription.unsubscribe()
    }
  }, [])

  const handleSignOut = async () => {
    await supabase.auth.signOut()
    setSession(null)
  }

  if (loading) {
    return (
      <div className="loading-screen" role="status">
        <div className="spinner"></div>
        <p>Loading Agentic RAG...</p>
      </div>
    )
  }

  if (!session) {
    return <AuthForm />
  }

  return (
    <ChatWorkspace
      userEmail={session.user.email || 'user@local'}
      onSignOut={handleSignOut}
    />
  )
}

export default App
