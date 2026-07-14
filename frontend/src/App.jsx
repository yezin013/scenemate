import { useState, useEffect } from 'react'
import { supabase } from './supabase'
import Login from './screens/Login'
import Track from './screens/Track'
import ArchiveScreen from './screens/ArchiveScreen'
import AnalysisScreen from './screens/AnalysisScreen'
import CompareScreen from './screens/CompareScreen'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// ── 최상위: 세션 감지 → Login or Main ────────────────────
export default function App() {
  const [session, setSession] = useState(undefined) // undefined=로딩, null=미로그인

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => setSession(session))
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_e, session) => {
      setSession(session)
    })
    return () => subscription.unsubscribe()
  }, [])

  if (session === undefined)
    return <div className="loading"><span className="spinner" />로딩 중…</div>
  if (!session) return <Login />
  return <Main token={session.access_token} />
}

// ── 메인 앱 ───────────────────────────────────────────────
function Main({ token }) {
  const auth = { Authorization: `Bearer ${token}` }

  const [photo, setPhoto] = useState(null)
  const [preview, setPreview] = useState('')
  const [selfIntro, setSelfIntro] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)
  const [genId, setGenId] = useState(0)

  const [archiveRefreshTick, setArchiveRefreshTick] = useState(0)

  const [isAdmin, setIsAdmin] = useState(false)
  const [showAdmin, setShowAdmin] = useState(false)

  // 분석 화면 상태: null | { script, result: null | analysisData }
  const [analysisView, setAnalysisView] = useState(null)

  useEffect(() => {
    fetch(`${API}/admin/check`, { headers: auth })
      .then(r => { if (r.ok) setIsAdmin(true) })
      .catch(() => {})
  }, [])

  function onPhoto(e) {
    const f = e.target.files[0]
    setPhoto(f)
    setPreview(f ? URL.createObjectURL(f) : '')
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError(''); setResult(null)
    if (!photo) { setError('사진을 선택해 주세요.'); return }
    setLoading(true)
    try {
      const fd = new FormData()
      fd.append('photo', photo)
      fd.append('self_intro', selfIntro)
      fd.append('save', 'false')
      const res = await fetch(`${API}/generate-from-photo`, { method: 'POST', headers: auth, body: fd })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body.detail || `서버 오류 ${res.status}`)
      }
      setResult(await res.json())
      setGenId(n => n + 1)
    } catch (err) {
      setError(err.message || '요청에 실패했어요. 백엔드가 켜져 있는지 확인해 주세요.')
    } finally {
      setLoading(false)
    }
  }

  async function saveTrack(data, trackKey) {
    const res = await fetch(`${API}/scripts`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...auth },
      body: JSON.stringify({
        script_text: data.script,
        source: 'ai',
        track: trackKey,
        title: data.title,
        setup: data.situation,
        fit_reason: data.objective,
        inputs: { appearance_keywords: result?.appearance_keywords ?? null, self_intro: selfIntro },
      }),
    })
    if (!res.ok) throw new Error(`저장 실패 ${res.status}`)
    setArchiveRefreshTick(t => t + 1)
    return res.json()
  }

  // 분석 화면 진입
  function openAnalysis(script) {
    setAnalysisView({ script, result: null })
  }

  // 분석 완료 → 비교 화면
  function onAnalysisComplete(data) {
    setAnalysisView(v => ({ ...v, result: data }))
  }

  // 분석 화면 닫기
  function closeAnalysis() {
    setAnalysisView(null)
  }

  // 분석 화면 렌더링
  if (analysisView) {
    const { script, result: analysisResult } = analysisView
    if (analysisResult) {
      return (
        <CompareScreen
          script={script}
          analysisResult={analysisResult}
          onBack={closeAnalysis}
          onReanalyze={() => setAnalysisView({ script, result: null })}
        />
      )
    }
    return (
      <AnalysisScreen
        script={script}
        token={token}
        onComplete={onAnalysisComplete}
        onBack={closeAnalysis}
      />
    )
  }

  return (
    <div className="page">
      <header className="hero">
        <span className="kicker">AI 오디션 독백 매칭</span>
        <h1 className="wordmark">SceneMate</h1>
        <p className="tagline">사진 · 자기소개, 두 가지로<br />나에게 꼭 맞는 독백 대사를 두 방향으로.</p>
        <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.75rem', justifyContent: 'center' }}>
          {isAdmin && (
            <button type="button" className="fb-cancel" style={{ fontSize: '0.8rem' }}
              onClick={() => setShowAdmin(v => !v)}>
              {showAdmin ? '관리자 패널 닫기' : '관리자 패널'}
            </button>
          )}
          <button type="button" className="fb-cancel" style={{ fontSize: '0.8rem' }}
            onClick={() => supabase.auth.signOut()}>
            로그아웃
          </button>
        </div>
      </header>

      <form onSubmit={handleSubmit} className="panel form">
        <div className="field">
          <span className="field-label">사진</span>
          <div className="upload">
            <input id="photo" type="file" accept="image/*" onChange={onPhoto} hidden />
            <label htmlFor="photo" className="upload-btn">
              {preview ? '다른 사진 선택' : '사진 선택하기'}
            </label>
            {preview && <img src={preview} alt="미리보기" className="thumb" />}
          </div>
          <p className="notice">
            업로드한 사진은 대사 분석에만 사용되며 분석 직후 폐기됩니다.
            사진 자체는 저장되지 않고, 창작된 대사만 아카이브에 저장돼요.
          </p>
        </div>

        <label className="field">
          <span className="field-label">자기소개 <em>성격 · 내면</em></span>
          <textarea rows={4} value={selfIntro} onChange={e => setSelfIntro(e.target.value)}
            placeholder="예: 밝고 장난기 많고 에너지가 넘쳐요. 겉은 차분한데 속은 욕심이 많아요." />
        </label>

        <button className="cta" disabled={loading}>
          {loading ? '대사를 짓는 중…' : '독백 대사 생성'}
        </button>
      </form>

      {error && <p className="error">{error}</p>}
      {loading && <div className="loading"><span className="spinner" />무대를 준비하고 있어요…</div>}

      {result && (
        <section className="results">
          {result.appearance_keywords && (
            <p className="kw"><span>외모 키워드</span>{result.appearance_keywords}</p>
          )}
          <div className="track-grid">
            <Track key={`a-${genId}`} tone="a" badge="A" label="외모 기반"
              trackKey="appearance" data={result.track_A_appearance} onSave={saveTrack} />
            <Track key={`b-${genId}`} tone="b" badge="B" label="성격 기반"
              trackKey="personality" data={result.track_B_personality} onSave={saveTrack} />
          </div>
        </section>
      )}

      <ArchiveScreen
        token={token} onAnalyze={openAnalysis} refreshSignal={archiveRefreshTick}
      />

      {showAdmin && <AdminPanel auth={auth} />}

      <footer className="foot">SceneMate · AI 오디션 독백 매칭</footer>
    </div>
  )
}

// ── 어드민 패널 ───────────────────────────────────────────
function AdminPanel({ auth }) {
  const [stats, setStats] = useState(null)
  const [scripts, setScripts] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    setLoading(true)
    Promise.all([
      fetch(`${API}/admin/stats`, { headers: auth }).then(r => r.json()),
      fetch(`${API}/admin/scripts`, { headers: auth }).then(r => r.json()),
    ])
      .then(([s, sc]) => { setStats(s); setScripts(sc) })
      .catch(() => setError('어드민 데이터를 불러오지 못했어요.'))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="loading"><span className="spinner" />어드민 데이터 로딩 중…</div>
  if (error) return <p className="error">{error}</p>

  return (
    <section className="archive" style={{ borderTop: '2px solid #f59e0b' }}>
      <h2 className="archive-title" style={{ color: '#f59e0b' }}>관리자 패널</h2>

      {stats && (
        <div style={{ display: 'flex', gap: '1.5rem', flexWrap: 'wrap', margin: '0.75rem 0' }}>
          <StatCard label="전체 대사" value={stats.total_scripts} />
          <StatCard label="가입 사용자" value={stats.total_users} />
          <StatCard label="외모 기반" value={stats.by_track?.appearance ?? 0} />
          <StatCard label="성격 기반" value={stats.by_track?.personality ?? 0} />
        </div>
      )}

      {scripts && (
        <div style={{ overflowX: 'auto', marginTop: '1rem' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid #374151' }}>
                {['ID', '사용자', '트랙', '제목', '날짜'].map(h => (
                  <th key={h} style={{ padding: '0.4rem 0.6rem', textAlign: 'left', color: '#9ca3af' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {scripts.map(s => (
                <tr key={s.id} style={{ borderBottom: '1px solid #1f2937' }}>
                  <td style={{ padding: '0.4rem 0.6rem' }}>{s.id}</td>
                  <td style={{ padding: '0.4rem 0.6rem', fontFamily: 'monospace', color: '#6b7280' }}>
                    {s.user_id ? s.user_id.slice(0, 8) + '…' : '-'}
                  </td>
                  <td style={{ padding: '0.4rem 0.6rem' }}>{s.track === 'appearance' ? '외모' : '성격'}</td>
                  <td style={{ padding: '0.4rem 0.6rem' }}>{s.title ?? '-'}</td>
                  <td style={{ padding: '0.4rem 0.6rem', color: '#6b7280' }}>
                    {(s.created_at ?? '').slice(0, 10)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}

function StatCard({ label, value }) {
  return (
    <div style={{ background: '#1f2937', borderRadius: '0.5rem', padding: '0.75rem 1.25rem', minWidth: '100px' }}>
      <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#f3f4f6' }}>{value}</div>
      <div style={{ fontSize: '0.75rem', color: '#9ca3af', marginTop: '0.2rem' }}>{label}</div>
    </div>
  )
}

