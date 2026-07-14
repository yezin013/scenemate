import { useState, useEffect } from 'react'
import { supabase } from './supabase'
import { apiFetch } from './api'
import Login from './screens/Login'
import GenerateScreen from './screens/GenerateScreen'
import AnalysisScreen from './screens/AnalysisScreen'
import CompareScreen from './screens/CompareScreen'

// ── 최상위: 세션 감지 + 화면 라우팅 ────────────────────────
export default function App() {
  const [session, setSession] = useState(undefined) // undefined=로딩, null=미로그인
  const [isAdmin, setIsAdmin] = useState(false)
  const [showAdmin, setShowAdmin] = useState(false)
  // 분석 화면 상태: null | { script, result: null | analysisData }
  const [analysisView, setAnalysisView] = useState(null)

  const token = session?.access_token

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => setSession(session))
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_e, session) => {
      setSession(session)
    })
    return () => subscription.unsubscribe()
  }, [])

  useEffect(() => {
    if (!token) return
    apiFetch('/admin/check', token)
      .then(r => { if (r.ok) setIsAdmin(true) })
      .catch(() => {})
  }, [token])

  if (session === undefined)
    return <div className="loading"><span className="spinner" />로딩 중…</div>
  if (!session) return <Login />

  if (analysisView) {
    const { script, result: analysisResult } = analysisView
    if (analysisResult) {
      return (
        <CompareScreen
          script={script}
          analysisResult={analysisResult}
          onBack={() => setAnalysisView(null)}
          onReanalyze={() => setAnalysisView({ script, result: null })}
        />
      )
    }
    return (
      <AnalysisScreen
        script={script}
        token={token}
        onComplete={data => setAnalysisView(v => ({ ...v, result: data }))}
        onBack={() => setAnalysisView(null)}
      />
    )
  }

  return (
    <GenerateScreen
      token={token}
      isAdmin={isAdmin}
      showAdmin={showAdmin}
      onToggleAdmin={() => setShowAdmin(v => !v)}
      onOpenAnalysis={script => setAnalysisView({ script, result: null })}
    />
  )
}
