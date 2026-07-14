import { LAYERS } from './AnalysisScreen'

// ── 비교 화면 ─────────────────────────────────────────────
export default function CompareScreen({ script, analysisResult, onBack, onReanalyze }) {
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
