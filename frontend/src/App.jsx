import { useState } from 'react'

// 백엔드 주소 — uvicorn 실행 포트와 맞춰야 함. (백엔드를 8000에서 띄우면 8000으로 변경)
const API = 'http://localhost:8001'

export default function App() {
  const [photo, setPhoto] = useState(null)
  const [selfIntro, setSelfIntro] = useState('')
  const [voiceTone, setVoiceTone] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setResult(null)
    if (!photo) { setError('사진을 선택해주세요.'); return }
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
      setError(err.message || '요청 실패 (백엔드가 켜져 있는지, 포트가 맞는지 확인하세요)')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h1>🎭 SceneMate</h1>
      <p className="sub">사진 · 자기소개 · 말투로 오디션 독백 두 개를 추천받아요</p>

      <form onSubmit={handleSubmit} className="card">
        <label>사진
          <input type="file" accept="image/*" onChange={(e) => setPhoto(e.target.files[0])} />
        </label>
        <label>자기소개 (성격)
          <textarea rows={3} value={selfIntro} onChange={(e) => setSelfIntro(e.target.value)}
            placeholder="예: 밝고 장난기 많고 에너지가 넘쳐요" />
        </label>
        <label>목소리 / 말투
          <input type="text" value={voiceTone} onChange={(e) => setVoiceTone(e.target.value)}
            placeholder="예: 높고 통통 튀는 톤, 빠른 말" />
        </label>
        <button disabled={loading}>{loading ? '생성 중...' : '대사 생성'}</button>
      </form>

      {error && <p className="error">⚠️ {error}</p>}

      {result && (
        <div className="results">
          {result.appearance_keywords && (
            <p className="kw">추출된 외모 키워드: {result.appearance_keywords}</p>
          )}
          <Track label="외모 기반" data={result.track_A_appearance} />
          <Track label="성격 기반" data={result.track_B_personality} />
        </div>
      )}
    </div>
  )
}

function Track({ label, data }) {
  return (
    <div className="track">
      <h2>{label} — {data.title}</h2>
      <p className="setup">상황: {data.situation}</p>
      <p className="meta">목적: {data.objective}</p>
      <p className="script">{data.script}</p>
      {data.voice_style && <p className="meta">목소리: {data.voice_style}</p>}
    </div>
  )
}
