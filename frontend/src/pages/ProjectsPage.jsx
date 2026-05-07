import { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { api } from '../api'

export default function ProjectsPage() {
  const [projects, setProjects] = useState([])
  const [rulesets, setRulesets] = useState([])
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ name: '', description: '', ruleset_id: '' })
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    loadProjects()
    api.getRulesets().then(({ data }) => setRulesets(data)).catch(() => {})
  }, [])

  async function loadProjects() {
    try {
      const { data } = await api.getProjects()
      setProjects(data)
    } catch (e) {
      console.error(e)
    }
  }

  async function handleCreate(e) {
    e.preventDefault()
    if (!form.name.trim()) return
    setLoading(true)
    try {
      await api.createProject({ ...form, ruleset_id: form.ruleset_id ? Number(form.ruleset_id) : null })
      setForm({ name: '', description: '', ruleset_id: '' })
      setShowForm(false)
      loadProjects()
    } finally {
      setLoading(false)
    }
  }

  const defaultRuleset = rulesets.find(r => r.is_default)

  return (
    <div className="page">
      <nav className="navbar">
        <span className="navbar-brand">🛡 Aegis QA</span>
        <div style={{ marginLeft: 'auto' }}>
          <Link to="/rulesets" style={{ fontSize: 13, color: '#6b7280', textDecoration: 'none',
            padding: '4px 12px', borderRadius: 6, border: '1px solid #e5e7eb', background: '#fff' }}>
            ⚙ QA 룰셋 관리
          </Link>
        </div>
      </nav>
      <div className="container">
        <div className="page-header">
          <h1>프로젝트</h1>
          <p>테스트케이스를 관리할 프로젝트를 선택하거나 새로 만드세요</p>
        </div>

        <div className="card">
          <div className="card-header">
            <span className="card-title">프로젝트 목록</span>
            <button className="btn btn-primary" onClick={() => setShowForm(!showForm)}>
              + 새 프로젝트
            </button>
          </div>

          {showForm && (
            <form onSubmit={handleCreate} style={{ marginBottom: 20, padding: '16px', background: '#f9fafb', borderRadius: 8 }}>
              <div className="form-group">
                <label>프로젝트명 *</label>
                <input
                  value={form.name}
                  onChange={e => setForm({ ...form, name: e.target.value })}
                  placeholder="예: XpERP 홈화면 리뉴얼"
                  autoFocus
                />
              </div>
              <div className="form-group">
                <label>설명</label>
                <input
                  value={form.description}
                  onChange={e => setForm({ ...form, description: e.target.value })}
                  placeholder="프로젝트 설명 (선택)"
                />
              </div>
              <div className="form-group">
                <label>QA 룰셋</label>
                <select value={form.ruleset_id} onChange={e => setForm({ ...form, ruleset_id: e.target.value })}
                  style={{ width: '100%', padding: '8px 12px', borderRadius: 6, border: '1px solid #d1d5db', fontSize: 14 }}>
                  <option value="">기본값 사용 {defaultRuleset ? `(${defaultRuleset.name})` : ''}</option>
                  {rulesets.map(r => (
                    <option key={r.id} value={r.id}>
                      {r.name}{r.is_default ? ' (기본값)' : ''}{r.service_type ? ` — ${r.service_type}` : ''}
                    </option>
                  ))}
                </select>
                <div style={{ fontSize: 11, color: '#9ca3af', marginTop: 4 }}>
                  선택한 룰셋이 메뉴트리 추출 및 TC 생성에 적용됩니다
                </div>
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                <button type="submit" className="btn btn-primary" disabled={loading}>
                  {loading ? <span className="spinner" /> : '생성'}
                </button>
                <button type="button" className="btn btn-outline" onClick={() => setShowForm(false)}>취소</button>
              </div>
            </form>
          )}

          {projects.length === 0 ? (
            <div className="empty">
              <div style={{ fontSize: 40 }}>📁</div>
              <p>프로젝트가 없습니다. 새 프로젝트를 만들어보세요.</p>
            </div>
          ) : (
            <div className="item-grid">
              {projects.map(p => (
                <div key={p.id} className="item-card" onClick={() => navigate(`/projects/${p.id}`)}>
                  <h3>{p.name}</h3>
                  {p.description && <p>{p.description}</p>}
                  <div className="meta" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: 11, color: '#9ca3af' }}>
                      {new Date(p.created_at).toLocaleDateString('ko-KR')}
                    </span>
                    {p.ruleset_id && (() => {
                      const rs = rulesets.find(r => r.id === p.ruleset_id)
                      return rs ? (
                        <span style={{ fontSize: 10, background: '#f0f9ff', color: '#0369a1',
                          padding: '2px 6px', borderRadius: 8, border: '1px solid #bae6fd' }}>
                          {rs.name}
                        </span>
                      ) : null
                    })()}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
