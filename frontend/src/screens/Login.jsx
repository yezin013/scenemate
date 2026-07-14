import { useState } from 'react'
import { supabase } from '../supabase'

// ── 로그인 / 회원가입 ─────────────────────────────────────
export default function Login() {
  const [mode, setMode] = useState('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  async function handleSubmit(e) {
    e.preventDefault()
    setError(''); setMessage('')
    setLoading(true)
    try {
      if (mode === 'login') {
        const { error } = await supabase.auth.signInWithPassword({ email, password })
        if (error) throw error
      } else {
        const { error } = await supabase.auth.signUp({ email, password })
        if (error) throw error
        setMessage('확인 이메일을 보냈어요. 메일함을 확인해 주세요.')
      }
    } catch (err) {
      setError(err.message || '오류가 발생했어요.')
    } finally {
      setLoading(false)
    }
  }

  function toggleMode() {
    setMode(m => m === 'login' ? 'signup' : 'login')
    setError(''); setMessage('')
  }

  return (
    <div className="page">
      <header className="hero">
        <span className="kicker">AI 오디션 독백 매칭</span>
        <h1 className="wordmark">SceneMate</h1>
        <p className="tagline">나에게 꼭 맞는 독백 대사를 두 방향으로.</p>
      </header>
      <form onSubmit={handleSubmit} className="panel form">
        <h2 className="field-label" style={{ fontSize: '1rem', marginBottom: '1rem' }}>
          {mode === 'login' ? '로그인' : '회원가입'}
        </h2>
        <label className="field">
          <span className="field-label">이메일</span>
          <input type="email" value={email} onChange={e => setEmail(e.target.value)} required />
        </label>
        <label className="field">
          <span className="field-label">비밀번호</span>
          <input type="password" value={password} onChange={e => setPassword(e.target.value)}
            required minLength={6} />
        </label>
        {error && <p className="error">{error}</p>}
        {message && <p className="notice">{message}</p>}
        <button className="cta" disabled={loading}>
          {loading ? '처리 중…' : mode === 'login' ? '로그인' : '회원가입'}
        </button>
        <button type="button" className="fb-cancel" style={{ marginTop: '0.5rem' }} onClick={toggleMode}>
          {mode === 'login' ? '계정이 없나요? 회원가입' : '이미 계정이 있나요? 로그인'}
        </button>
      </form>
    </div>
  )
}
