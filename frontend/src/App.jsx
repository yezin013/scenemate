import { useState, useEffect } from 'react'
import { supabase } from './supabase'
import Login from './screens/Login'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const LAYERS = [
  { key: 'subtext',      label: '서브텍스트',  desc: '대사 이면의 실제 의미는 무엇인가?' },
  { key: 'action_verb',  label: '행동 동사',   desc: '인물이 하는 핵심 행동 — "설득하다", "지배하다" 등' },
  { key: 'emotion_arc',  label: '감정선 흐름', desc: '장면을 통해 감정이 어떻게 변화하는가' },
  { key: 'context',      label: '상황·전사',   desc: '이 대사가 펼쳐지는 상황과 직전까지의 사건' },
  { key: 'character_bg', label: '인물 배경',   desc: '이 대사를 만든 인물의 역사와 내면' },
  { key: 'relationship', label: '관계 분석',   desc: '상대방과의 권력관계, 감정적 역학' },
  { key: 'real_goal',    label: '진짜 목표',   desc: '표면적 원하는 것 너머의 진짜 욕구' },
]

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

  const [archive, setArchive] = useState(null)
  const [archiveLoading, setArchiveLoading] = useState(false)
  const [archiveError, setArchiveError] = useState('')

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
    if (archive !== null) loadArchive()
    return res.json()
  }

  async function loadArchive() {
    setArchiveLoading(true); setArchiveError('')
    try {
      const res = await fetch(`${API}/scripts`, { headers: auth })
      if (!res.ok) throw new Error(`조회 실패 ${res.status}`)
      setArchive(await res.json())
    } catch (err) {
      setArchiveError(err.message || '아카이브를 불러오지 못했어요.')
    } finally {
      setArchiveLoading(false)
    }
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

      <Archive
        data={archive} loading={archiveLoading} error={archiveError}
        onOpen={loadArchive} onRefresh={loadArchive} auth={auth}
        onAnalyze={openAnalysis}
      />

      {showAdmin && <AdminPanel auth={auth} />}

      <footer className="foot">SceneMate · AI 오디션 독백 매칭</footer>
    </div>
  )
}

// ── 트랙 카드 ─────────────────────────────────────────────
function Track({ tone, badge, label, trackKey, data, onSave }) {
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [err, setErr] = useState('')

  async function handleSave() {
    setSaving(true); setErr('')
    try { await onSave(data, trackKey); setSaved(true) }
    catch { setErr('저장에 실패했어요.') }
    finally { setSaving(false) }
  }

  return (
    <article className={`track track-${tone}`}>
      <header className="track-head">
        <span className="badge">{badge}</span>
        <h2 className="track-title">{label}</h2>
      </header>
      <dl className="track-meta">
        <div><dt>상황</dt><dd>{data.situation}</dd></div>
        <div><dt>목적</dt><dd>{data.objective}</dd></div>
      </dl>
      <p className="script">{data.script}</p>
      <div className="track-foot">
        <button type="button" className="save-btn" onClick={handleSave} disabled={saving || saved}>
          {saved ? '✓ 아카이브에 저장됨' : saving ? '저장 중…' : '아카이브에 저장'}
        </button>
        {err && <span className="save-err">{err}</span>}
      </div>
    </article>
  )
}

// ── 아카이브 ──────────────────────────────────────────────
const TRACK_LABEL = { appearance: '외모 기반', personality: '성격 기반' }

function Archive({ data, loading, error, onOpen, onRefresh, auth, onAnalyze }) {
  return (
    <section className="archive">
      <div className="archive-head">
        <h2 className="archive-title">내 아카이브</h2>
        <button type="button" className="archive-toggle" onClick={onOpen} disabled={loading}>
          {loading ? '불러오는 중…' : data === null ? '아카이브 보기' : '새로고침'}
        </button>
      </div>
      {error && <p className="error">{error}</p>}
      {data !== null && !loading && (
        data.length === 0
          ? <p className="archive-empty">아직 저장한 대사가 없어요. 마음에 드는 트랙을 저장해 보세요.</p>
          : <ul className="archive-list">
            {data.map(s => (
              <ArchiveItem key={s.id} s={s} onRefresh={onRefresh} auth={auth} onAnalyze={onAnalyze} />
            ))}
          </ul>
      )}
    </section>
  )
}

function ArchiveItem({ s, onRefresh, auth, onAnalyze }) {
  const [similar, setSimilar] = useState(null)
  const [simLoading, setSimLoading] = useState(false)

  async function toggleSimilar() {
    if (similar !== null) { setSimilar(null); return }
    setSimLoading(true)
    try {
      const res = await fetch(`${API}/scripts/${s.id}/similar`, { headers: auth })
      setSimilar(res.ok ? await res.json() : [])
    } catch { setSimilar([]) }
    finally { setSimLoading(false) }
  }

  return (
    <li className={`archive-item track-${s.track === 'personality' ? 'b' : 'a'}`}>
      <div className="archive-item-head">
        <span className="archive-track">{TRACK_LABEL[s.track] ?? s.track ?? '대사'}</span>
        {s.title && <span className="archive-item-title">{s.title}</span>}
        <span className="archive-date">{(s.created_at ?? '').slice(0, 10)}</span>
      </div>
      {s.setup && <p className="archive-setup">{s.setup}</p>}
      <p className="archive-script">{s.script_text}</p>
      <div style={{ marginTop: '12px', display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
        <button type="button" className="analyze-btn" onClick={() => onAnalyze(s)}>
          분석하기
        </button>
        <button type="button" className="similar-btn" onClick={toggleSimilar} disabled={simLoading}>
          {simLoading ? '찾는 중…' : similar !== null ? '비슷한 대사 닫기' : '비슷한 대사'}
        </button>
      </div>
      {similar !== null && (
        <div className="similar-list">
          {similar.length === 0 ? (
            <p className="similar-empty">비슷한 대사가 없어요. 대사를 더 저장하면 비교할 수 있어요.</p>
          ) : similar.map(sim => (
            <div key={sim.id} className="similar-item">
              <div className="similar-item-head">
                <span className="archive-track" style={{ color: sim.track === 'personality' ? 'var(--violet)' : undefined }}>
                  {TRACK_LABEL[sim.track] ?? '대사'}
                </span>
                {sim.title && <span className="archive-item-title" style={{ fontSize: '13px' }}>{sim.title}</span>}
                <span className="similar-score">{Math.round(sim.similarity * 100)}% 유사</span>
              </div>
              {sim.setup && <p className="archive-setup" style={{ margin: '4px 0 6px' }}>{sim.setup}</p>}
              <p className="archive-script" style={{ fontSize: '13.5px' }}>{sim.script_text}</p>
            </div>
          ))}
        </div>
      )}
      <FeedbackSection script={s} onRefresh={onRefresh} auth={auth} />
    </li>
  )
}

// ── 오디션 피드백 ─────────────────────────────────────────
const RESULT_CLASS = { 합격: 'pass', 불합격: 'fail', 대기: 'wait' }

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

// ── 오디션 피드백 ─────────────────────────────────────────
function FeedbackSection({ script, onRefresh, auth }) {
  const [open, setOpen] = useState(false)
  const [date, setDate] = useState('')
  const [venue, setVenue] = useState('')
  const [result, setResult] = useState('')
  const [memo, setMemo] = useState('')
  const [saving, setSaving] = useState(false)
  const [err, setErr] = useState('')

  const items = script.feedback ?? []

  async function submit(e) {
    e.preventDefault(); setErr('')
    if (!date && !venue && !result && !memo.trim()) {
      setErr('내용을 한 가지 이상 입력해 주세요.'); return
    }
    setSaving(true)
    try {
      const res = await fetch(`${API}/scripts/${script.id}/feedback`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', ...auth },
        body: JSON.stringify({ date: date || null, venue: venue || null, result: result || null, memo: memo.trim() || null }),
      })
      if (!res.ok) throw new Error(`저장 실패 ${res.status}`)
      setDate(''); setVenue(''); setResult(''); setMemo(''); setOpen(false)
      onRefresh?.()
    } catch { setErr('피드백 저장에 실패했어요.') }
    finally { setSaving(false) }
  }

  return (
    <div className="fb">
      {items.length > 0 && (
        <ul className="fb-list">
          {items.map((f, i) => (
            <li key={i} className="fb-item">
              <div className="fb-meta">
                {f.result && <span className={`fb-result fb-${RESULT_CLASS[f.result] ?? 'wait'}`}>{f.result}</span>}
                {f.date && <span className="fb-date">{f.date}</span>}
                {f.venue && <span className="fb-venue">{f.venue}</span>}
              </div>
              {f.memo && <p className="fb-memo">{f.memo}</p>}
            </li>
          ))}
        </ul>
      )}
      {open ? (
        <form className="fb-form" onSubmit={submit}>
          <div className="fb-row">
            <input type="date" value={date} onChange={e => setDate(e.target.value)} />
            <select value={result} onChange={e => setResult(e.target.value)}>
              <option value="">결과 선택</option>
              <option value="합격">합격</option>
              <option value="불합격">불합격</option>
              <option value="대기">대기</option>
            </select>
          </div>
          <input type="text" placeholder="작품·오디션명 (선택)" value={venue}
            onChange={e => setVenue(e.target.value)} />
          <textarea rows={2} placeholder="메모 — 피드백·소감 등 (선택)" value={memo}
            onChange={e => setMemo(e.target.value)} />
          {err && <span className="save-err">{err}</span>}
          <div className="fb-actions">
            <button type="submit" className="save-btn" disabled={saving}>
              {saving ? '저장 중…' : '피드백 저장'}
            </button>
            <button type="button" className="fb-cancel" onClick={() => { setOpen(false); setErr('') }}>취소</button>
          </div>
        </form>
      ) : (
        <button type="button" className="fb-add" onClick={() => setOpen(true)}>+ 피드백 추가</button>
      )}
    </div>
  )
}

// ── 대사 분석 화면 ────────────────────────────────────────
function AnalysisScreen({ script, token, onComplete, onBack }) {
  const auth = { Authorization: `Bearer ${token}` }
  const initLayers = Object.fromEntries(LAYERS.map(l => [l.key, '']))
  const [layers, setLayers] = useState(initLayers)
  const [hints, setHints] = useState({})
  const [hintLoading, setHintLoading] = useState({})
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  // 기존 분석이 있으면 불러와서 채우기
  useEffect(() => {
    fetch(`${API}/scripts/${script.id}/analyze/full`, { headers: auth })
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (data?.user_analysis) {
          setLayers(Object.fromEntries(LAYERS.map(l => [l.key, data.user_analysis[l.key] || ''])))
        }
      })
      .catch(() => {})
  }, [script.id]) // eslint-disable-line react-hooks/exhaustive-deps

  async function requestHint(layerKey) {
    setHintLoading(h => ({ ...h, [layerKey]: true }))
    try {
      const res = await fetch(`${API}/scripts/${script.id}/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...auth },
        body: JSON.stringify({ layer: layerKey, draft: layers[layerKey] }),
      })
      if (!res.ok) throw new Error()
      const data = await res.json()
      setHints(h => ({ ...h, [layerKey]: data.hint }))
    } catch {
      setHints(h => ({ ...h, [layerKey]: '힌트를 불러오지 못했어요. 다시 시도해 주세요.' }))
    } finally {
      setHintLoading(h => ({ ...h, [layerKey]: false }))
    }
  }

  async function handleSubmit() {
    setSubmitting(true); setError('')
    try {
      const res = await fetch(`${API}/scripts/${script.id}/analyze/full`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...auth },
        body: JSON.stringify(layers),
      })
      if (!res.ok) throw new Error(`오류 ${res.status}`)
      onComplete(await res.json())
    } catch {
      setError('분석 저장 중 오류가 발생했어요. 다시 시도해 주세요.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="page">
      <header className="hero" style={{ paddingBottom: '20px' }}>
        <span className="kicker">대사 분석</span>
        <h1 className="wordmark" style={{ fontSize: 'clamp(30px, 6vw, 50px)' }}>
          {script.title || '무제'}
        </h1>
        {script.setup && <p className="tagline" style={{ marginTop: '8px' }}>{script.setup}</p>}
      </header>

      <div className="panel" style={{ padding: '16px 20px', marginBottom: '20px' }}>
        <p className="archive-script" style={{ margin: 0 }}>{script.script_text}</p>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '20px', flexWrap: 'wrap' }}>
        <button type="button" className="fb-cancel" onClick={onBack}>← 돌아가기</button>
        <span style={{ fontSize: '13px', color: 'var(--muted)' }}>
          7개 레이어를 직접 분석하고, 막히면 힌트를 받아보세요.
        </span>
      </div>

      <div className="layer-list">
        {LAYERS.map(layer => (
          <div key={layer.key} className="panel layer-card">
            <div className="layer-card-head">
              <div>
                <span className="layer-label">{layer.label}</span>
                <span className="layer-desc">{layer.desc}</span>
              </div>
              <button
                type="button"
                className="hint-btn"
                onClick={() => requestHint(layer.key)}
                disabled={hintLoading[layer.key]}
              >
                {hintLoading[layer.key] ? '로딩…' : '힌트'}
              </button>
            </div>
            <textarea
              rows={3}
              placeholder={`${layer.label}를 분석해 보세요…`}
              value={layers[layer.key]}
              onChange={e => setLayers(l => ({ ...l, [layer.key]: e.target.value }))}
            />
            {hints[layer.key] && (
              <div className="hint-box">
                <span className="hint-badge">힌트</span>
                <p className="hint-text">{hints[layer.key]}</p>
              </div>
            )}
          </div>
        ))}
      </div>

      {error && <p className="error">{error}</p>}

      <button
        className="cta"
        style={{ width: '100%', marginTop: '24px' }}
        onClick={handleSubmit}
        disabled={submitting}
      >
        {submitting ? 'AI 분석 중…' : '분석 완료 — AI와 비교하기'}
      </button>
    </div>
  )
}

// ── 비교 화면 ─────────────────────────────────────────────
function CompareScreen({ script, analysisResult, onBack, onReanalyze }) {
  return (
    <div className="page">
      <header className="hero" style={{ paddingBottom: '20px' }}>
        <span className="kicker">분석 비교</span>
        <h1 className="wordmark" style={{ fontSize: 'clamp(30px, 6vw, 50px)' }}>
          {script.title || '무제'}
        </h1>
      </header>

      <div style={{ display: 'flex', gap: '10px', marginBottom: '20px', flexWrap: 'wrap' }}>
        <button type="button" className="fb-cancel" onClick={onBack}>← 아카이브로</button>
        <button type="button" className="save-btn" onClick={onReanalyze}>다시 분석</button>
      </div>

      <div className="panel" style={{ padding: '16px 20px', marginBottom: '24px' }}>
        <p className="archive-script" style={{ margin: 0 }}>{script.script_text}</p>
      </div>

      <div className="compare-header">
        <div className="compare-col-label compare-col-user">내 분석</div>
        <div className="compare-col-label compare-col-ai">AI 분석</div>
      </div>

      <div className="compare-list">
        {LAYERS.map(layer => (
          <div key={layer.key} className="panel compare-row">
            <p className="layer-label" style={{ margin: '0 0 12px' }}>{layer.label}</p>
            <div className="compare-grid">
              <div className="compare-cell compare-cell-user">
                {analysisResult.user_analysis[layer.key]
                  ? <p className="compare-text">{analysisResult.user_analysis[layer.key]}</p>
                  : <p className="compare-empty">(작성 안 함)</p>}
              </div>
              <div className="compare-cell compare-cell-ai">
                <p className="compare-text">{analysisResult.ai_analysis[layer.key] || '—'}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      <footer className="foot">SceneMate · 대사 분석</footer>
    </div>
  )
}
