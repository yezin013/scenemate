import { useState } from 'react'

// 백엔드 주소 — uvicorn 실행 포트와 맞춰야 함. (백엔드를 8000에서 띄우면 8000으로 변경)
const API = 'http://localhost:8001'

export default function App() {
  const [photo, setPhoto] = useState(null)
  const [preview, setPreview] = useState('')
  const [selfIntro, setSelfIntro] = useState('')
  const [voiceTone, setVoiceTone] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)

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
      fd.append('voice_tone', voiceTone)
      fd.append('save', 'false')
      const res = await fetch(`${API}/generate-from-photo`, { method: 'POST', body: fd })
      if (!res.ok) throw new Error(`서버 오류 ${res.status}`)
      setResult(await res.json())
    } catch (err) {
      setError(err.message || '요청에 실패했어요. 백엔드가 켜져 있는지 확인해 주세요.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page">
      <header className="hero">
        <span className="kicker">AI 오디션 독백 매칭</span>
        <h1 className="wordmark">SceneMate</h1>
        <p className="tagline">사진 · 자기소개 · 목소리, 세 가지로<br />나에게 꼭 맞는 독백 대사를 두 방향으로.</p>
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
          <textarea rows={3} value={selfIntro} onChange={(e) => setSelfIntro(e.target.value)}
            placeholder="예: 밝고 장난기 많고 에너지가 넘쳐요. 겉은 차분한데 속은 욕심이 많아요." />
        </label>

        <label className="field">
          <span className="field-label">목소리 · 말투</span>
          <input type="text" value={voiceTone} onChange={(e) => setVoiceTone(e.target.value)}
            placeholder="예: 낮고 차분한 톤, 또박또박한 발음" />
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
            <Track tone="a" badge="A" label="외모 기반" data={result.track_A_appearance} />
            <Track tone="b" badge="B" label="성격 기반" data={result.track_B_personality} />
          </div>
        </section>
      )}

      <footer className="foot">SceneMate · AI 오디션 독백 매칭</footer>
    </div>
  )
}

function Track({ tone, badge, label, data }) {
  return (
    <article className={`track track-${tone}`}>
      <header className="track-head">
        <span className="badge">{badge}</span>
        <div>
          <span className="track-label">{label}</span>
          <h2 className="track-title">{data.title}</h2>
        </div>
      </header>
      <dl className="track-meta">
        <div><dt>상황</dt><dd>{data.situation}</dd></div>
        <div><dt>목적</dt><dd>{data.objective}</dd></div>
      </dl>
      <p className="script">{data.script}</p>
      {data.voice_style && <p className="voice">🎙 {data.voice_style}</p>}
    </article>
  )
}
