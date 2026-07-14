import { useState, useEffect } from 'react'
import { apiFetch } from '../api'

// ── 어드민 패널 ───────────────────────────────────────────
export default function AdminPanel({ token }) {
  const [stats, setStats] = useState(null)
  const [scripts, setScripts] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    setLoading(true)
    Promise.all([
      apiFetch('/admin/stats', token).then(r => r.json()),
      apiFetch('/admin/scripts', token).then(r => r.json()),
    ])
      .then(([s, sc]) => { setStats(s); setScripts(sc) })
      .catch(() => setError('어드민 데이터를 불러오지 못했어요.'))
      .finally(() => setLoading(false))
  }, [token])

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
