import { useState } from 'react'

// ── 트랙 카드 ─────────────────────────────────────────────
// 임시 위치: Main 해체 시 GenerateScreen.jsx로 병합되며 이 파일은 삭제됩니다.
export default function Track({ tone, badge, label, trackKey, data, onSave }) {
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
