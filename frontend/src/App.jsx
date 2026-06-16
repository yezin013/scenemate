import { useState } from 'react'

// 백엔드 주소 — .env(VITE_API_URL)로 덮어쓸 수 있음. 기본은 uvicorn 기본 포트(8000).
const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function App() {
  const [photo, setPhoto] = useState(null)
  const [preview, setPreview] = useState('')
  const [selfIntro, setSelfIntro] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)
  const [genId, setGenId] = useState(0)   // 생성마다 증가 → 트랙 저장상태 초기화용

  // 아카이브
  const [archive, setArchive] = useState(null)   // null=미조회, []=조회됨
  const [archiveLoading, setArchiveLoading] = useState(false)
  const [archiveError, setArchiveError] = useState('')

  function onPhoto(e) {
    const f = e.target.files[0]
    setPhoto(f)
    setPreview(f ? URL.createObjectURL(f) : '')
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setResult(null)
    if (!photo) { setError('사진을 선택해 주세요.'); return }
    setLoading(true)
    try {
      const fd = new FormData()
      fd.append('photo', photo)
      fd.append('self_intro', selfIntro)
      fd.append('save', 'false')
      const res = await fetch(`${API}/generate-from-photo`, { method: 'POST', body: fd })
      if (!res.ok) throw new Error(`서버 오류 ${res.status}`)
      setResult(await res.json())
      setGenId((n) => n + 1)
    } catch (err) {
      setError(err.message || '요청에 실패했어요. 백엔드가 켜져 있는지 확인해 주세요.')
    } finally {
      setLoading(false)
    }
  }

  // 트랙 한 개를 아카이브에 저장 (POST /scripts). 백엔드 자동저장과 동일한 컬럼 매핑.
  async function saveTrack(data, trackKey) {
    const res = await fetch(`${API}/scripts`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        script_text: data.script,
        source: 'ai',
        track: trackKey,            // 'appearance' | 'personality'
        title: data.title,
        setup: data.situation,      // 상황 → setup
        fit_reason: data.objective, // 목적 → fit_reason
        inputs: {
          appearance_keywords: result?.appearance_keywords ?? null,
          self_intro: selfIntro,
        },
      }),
    })
    if (!res.ok) throw new Error(`저장 실패 ${res.status}`)
    // 아카이브를 이미 펼쳐 본 상태면 목록 갱신
    if (archive !== null) loadArchive()
    return res.json()
  }

  async function loadArchive() {
    setArchiveLoading(true)
    setArchiveError('')
    try {
      const res = await fetch(`${API}/scripts`)
      if (!res.ok) throw new Error(`조회 실패 ${res.status}`)
      setArchive(await res.json())
    } catch (err) {
      setArchiveError(err.message || '아카이브를 불러오지 못했어요.')
    } finally {
      setArchiveLoading(false)
    }
  }

  return (
    <div className="page">
      <header className="hero">
        <span className="kicker">AI 오디션 독백 매칭</span>
        <h1 className="wordmark">SceneMate</h1>
        <p className="tagline">사진 · 자기소개, 두 가지로<br />나에게 꼭 맞는 독백 대사를 두 방향으로.</p>
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
        </div>

        <label className="field">
          <span className="field-label">자기소개 <em>성격 · 내면</em></span>
          <textarea rows={4} value={selfIntro} onChange={(e) => setSelfIntro(e.target.value)}
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
        data={archive}
        loading={archiveLoading}
        error={archiveError}
        onOpen={loadArchive}
      />

      <footer className="foot">SceneMate · AI 오디션 독백 매칭</footer>
    </div>
  )
}

function Track({ tone, badge, label, trackKey, data, onSave }) {
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [err, setErr] = useState('')

  async function handleSave() {
    setSaving(true)
    setErr('')
    try {
      await onSave(data, trackKey)
      setSaved(true)
    } catch {
      setErr('저장에 실패했어요.')
    } finally {
      setSaving(false)
    }
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

const TRACK_LABEL = { appearance: '외모 기반', personality: '성격 기반' }

function Archive({ data, loading, error, onOpen }) {
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
            {data.map((s) => (
              <li key={s.id} className={`archive-item track-${s.track === 'personality' ? 'b' : 'a'}`}>
                <div className="archive-item-head">
                  <span className="archive-track">{TRACK_LABEL[s.track] ?? s.track ?? '대사'}</span>
                  {s.title && <span className="archive-item-title">{s.title}</span>}
                  <span className="archive-date">{(s.created_at ?? '').slice(0, 10)}</span>
                </div>
                {s.setup && <p className="archive-setup">{s.setup}</p>}
                <p className="archive-script">{s.script_text}</p>
              </li>
            ))}
          </ul>
      )}
    </section>
  )
}
