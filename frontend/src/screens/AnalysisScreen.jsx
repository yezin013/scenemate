import { useState, useEffect } from 'react'
import { apiFetch } from '../api'

export const LAYERS = [
  { key: 'subtext',      label: '서브텍스트',  desc: '대사 이면의 실제 의미는 무엇인가?' },
  { key: 'action_verb',  label: '행동 동사',   desc: '인물이 하는 핵심 행동 — "설득하다", "지배하다" 등' },
  { key: 'emotion_arc',  label: '감정선 흐름', desc: '장면을 통해 감정이 어떻게 변화하는가' },
  { key: 'context',      label: '상황·전사',   desc: '이 대사가 펼쳐지는 상황과 직전까지의 사건' },
  { key: 'character_bg', label: '인물 배경',   desc: '이 대사를 만든 인물의 역사와 내면' },
  { key: 'relationship', label: '관계 분석',   desc: '상대방과의 권력관계, 감정적 역학' },
  { key: 'real_goal',    label: '진짜 목표',   desc: '표면적 원하는 것 너머의 진짜 욕구' },
]

// ── 대사 분석 화면 ────────────────────────────────────────
export default function AnalysisScreen({ script, token, onComplete, onBack }) {
  const initLayers = Object.fromEntries(LAYERS.map(l => [l.key, '']))
  const [layers, setLayers] = useState(initLayers)
  const [hints, setHints] = useState({})
  const [hintLoading, setHintLoading] = useState({})
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  // 기존 분석이 있으면 불러와서 채우기
  useEffect(() => {
    apiFetch(`/scripts/${script.id}/analyze/full`, token)
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
      const res = await apiFetch(`/scripts/${script.id}/analyze`, token, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
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
      const res = await apiFetch(`/scripts/${script.id}/analyze/full`, token, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
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
