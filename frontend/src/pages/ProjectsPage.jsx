import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'

export default function ProjectsPage() {
  const [projects, setProjects] = useState([])
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ name: '', description: '' })
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  useEffect(() => { loadProjects() }, [])

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
      await api.createProject(form)
      setForm({ name: '', description: '' })
      setShowForm(false)
      loadProjects()
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page">
      <nav className="navbar">
        <span className="navbar-brand">🛡 Aegis QA</span>
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
                  <div className="meta">
                    <span style={{ fontSize: 11, color: '#9ca3af' }}>
                      {new Date(p.created_at).toLocaleDateString('ko-KR')}
                    </span>
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
