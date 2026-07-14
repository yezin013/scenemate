import { useState, useEffect } from 'react'
import { apiFetch } from '../api'

const TRACK_LABEL = { appearance: '외모 기반', personality: '성격 기반' }
const RESULT_CLASS = { 합격: 'pass', 불합격: 'fail', 대기: 'wait' }

// ── 아카이브 (자체 상태 소유: archive/archiveLoading/archiveError) ──
export default function ArchiveScreen({ token, onAnalyze, refreshSignal }) {
  const [archive, setArchive] = useState(null)
  const [archiveLoading, setArchiveLoading] = useState(false)
  const [archiveError, setArchiveError] = useState('')

  async function loadArchive() {
    setArchiveLoading(true); setArchiveError('')
    try {
      const res = await apiFetch('/scripts', token)
      if (!res.ok) throw new Error(`조회 실패 ${res.status}`)
      setArchive(await res.json())
    } catch (err) {
      setArchiveError(err.message || '아카이브를 불러오지 못했어요.')
    } finally {
      setArchiveLoading(false)
    }
  }

  // 생성 화면에서 새로 저장된 트랙이 있으면(refreshSignal 변경), 이미 열려 있던 아카이브만 새로고침
  useEffect(() => {
    if (refreshSignal === undefined) return
    if (archive !== null) loadArchive()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refreshSignal])

  return (
    <section className="archive">
      <div className="archive-head">
        <h2 className="archive-title">내 아카이브</h2>
        <button type="button" className="archive-toggle" onClick={loadArchive} disabled={archiveLoading}>
          {archiveLoading ? '불러오는 중…' : archive === null ? '아카이브 보기' : '새로고침'}
        </button>
      </div>
      {archiveError && <p className="error">{archiveError}</p>}
      {archive !== null && !archiveLoading && (
        archive.length === 0
          ? <p className="archive-empty">아직 저장한 대사가 없어요. 마음에 드는 트랙을 저장해 보세요.</p>
          : <ul className="archive-list">
            {archive.map(s => (
              <ArchiveItem key={s.id} s={s} onRefresh={loadArchive} token={token} onAnalyze={onAnalyze} />
            ))}
          </ul>
      )}
    </section>
  )
}

function ArchiveItem({ s, onRefresh, token, onAnalyze }) {
  const [similar, setSimilar] = useState(null)
  const [simLoading, setSimLoading] = useState(false)

  async function toggleSimilar() {
    if (similar !== null) { setSimilar(null); return }
    setSimLoading(true)
    try {
      const res = await apiFetch(`/scripts/${s.id}/similar`, token)
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
      <FeedbackSection script={s} onRefresh={onRefresh} token={token} />
    </li>
  )
}

// ── 오디션 피드백 ─────────────────────────────────────────
function FeedbackSection({ script, onRefresh, token }) {
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
      const res = await apiFetch(`/scripts/${script.id}/feedback`, token, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
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
