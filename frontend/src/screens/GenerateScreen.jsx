import { useState } from 'react'
import { supabase } from '../supabase'
import { apiFetch } from '../api'
import ArchiveScreen from './ArchiveScreen'
import AdminPanel from './AdminPanel'

// ── 생성 화면 ─────────────────────────────────────────────
export default function GenerateScreen({ token, isAdmin, showAdmin, onToggleAdmin, onOpenAnalysis }) {
  const [photo, setPhoto] = useState(null)
  const [preview, setPreview] = useState('')
  const [selfIntro, setSelfIntro] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)
  const [genId, setGenId] = useState(0)

  const [archiveRefreshTick, setArchiveRefreshTick] = useState(0)

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
      const res = await apiFetch('/generate-from-photo', token, { method: 'POST', body: fd })
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
    const res = await apiFetch('/scripts', token, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
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

  return (
    <div className="page">
      <header className="hero">
        <span className="kicker">AI 오디션 독백 매칭</span>
        <h1 className="wordmark">SceneMate</h1>
        <p className="tagline">사진 · 자기소개, 두 가지로<br />나에게 꼭 맞는 독백 대사를 두 방향으로.</p>
        <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.75rem', justifyContent: 'center' }}>
          {isAdmin && (
            <button type="button" className="fb-cancel" style={{ fontSize: '0.8rem' }}
              onClick={onToggleAdmin}>
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
        token={token} onAnalyze={onOpenAnalysis} refreshSignal={archiveRefreshTick}
      />

      {showAdmin && <AdminPanel token={token} />}

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
