import { useState, useEffect, useMemo } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { api } from '../api'

const PAGE_SIZE_OPTIONS = [10, 20, 50]

export default function ProjectsPage() {
  const [projects, setProjects] = useState([])
  const [rulesets, setRulesets] = useState([])
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ name: '', description: '', ruleset_id: '' })
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
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
  const rulesetMap = useMemo(() => Object.fromEntries(rulesets.map(r => [r.id, r])), [rulesets])

  // 검색 필터링
  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase()
    if (!q) return projects
    return projects.filter(p =>
      (p.name || '').toLowerCase().includes(q) ||
      (p.description || '').toLowerCase().includes(q)
    )
  }, [projects, search])

  // 페이지네이션 계산
  const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize))
  const currentPage = Math.min(page, totalPages)
  const pageItems = filtered.slice((currentPage - 1) * pageSize, currentPage * pageSize)

  // 검색·페이지크기 변경 시 1페이지로 리셋
  useEffect(() => { setPage(1) }, [search, pageSize])

  function buildPageNumbers() {
    // 최대 7개까지: 1 … (cur-1) cur (cur+1) … last
    if (totalPages <= 7) return Array.from({ length: totalPages }, (_, i) => i + 1)
    const pages = new Set([1, totalPages, currentPage, currentPage - 1, currentPage + 1])
    const sorted = [...pages].filter(n => n >= 1 && n <= totalPages).sort((a, b) => a - b)
    const result = []
    for (let i = 0; i < sorted.length; i++) {
      if (i > 0 && sorted[i] - sorted[i - 1] > 1) result.push('…')
      result.push(sorted[i])
    }
    return result
  }

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
            <>
              {/* 검색 + 페이지크기 */}
              <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 12, flexWrap: 'wrap' }}>
                <input
                  value={search}
                  onChange={e => setSearch(e.target.value)}
                  placeholder="🔍 프로젝트명·설명 검색"
                  style={{
                    flex: '1 1 240px', padding: '8px 12px', borderRadius: 6,
                    border: '1px solid #d1d5db', fontSize: 13,
                  }}
                />
                <select
                  value={pageSize}
                  onChange={e => setPageSize(Number(e.target.value))}
                  style={{ padding: '8px 10px', borderRadius: 6, border: '1px solid #d1d5db', fontSize: 13 }}
                >
                  {PAGE_SIZE_OPTIONS.map(n => <option key={n} value={n}>{n}개씩</option>)}
                </select>
                <span style={{ fontSize: 12, color: '#6b7280' }}>
                  총 <strong style={{ color: '#111827' }}>{filtered.length}</strong>개
                  {search && <> · 전체 {projects.length}개 중</>}
                </span>
              </div>

              {/* 리스트(테이블) */}
              {filtered.length === 0 ? (
                <div className="empty" style={{ padding: '32px 0' }}>
                  <p style={{ fontSize: 13, color: '#6b7280' }}>검색 결과가 없습니다.</p>
                </div>
              ) : (
                <table className="tc-table">
                  <thead>
                    <tr>
                      <th style={{ width: 80 }}>Proj-ID</th>
                      <th style={{ width: '32%' }}>프로젝트명</th>
                      <th>설명</th>
                      <th style={{ width: 240 }}>룰셋</th>
                      <th style={{ width: 110 }}>생성일</th>
                    </tr>
                  </thead>
                  <tbody>
                    {pageItems.map(p => {
                      const rs = p.ruleset_id ? rulesetMap[p.ruleset_id] : null
                      return (
                        <tr key={p.id} className="tc-row" onClick={() => navigate(`/projects/${p.id}`)}>
                          <td style={{
                            color: '#9ca3af', fontFamily: 'monospace', fontSize: 12,
                            textAlign: 'center',
                          }}>{p.id}</td>
                          <td>
                            <span style={{ fontWeight: 600, color: '#111827' }}>{p.name}</span>
                          </td>
                          <td style={{
                            color: '#6b7280', fontSize: 13,
                            maxWidth: 320, overflow: 'hidden',
                            textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                          }} title={p.description || ''}>
                            {p.description || <span style={{ color: '#d1d5db' }}>—</span>}
                          </td>
                          <td>
                            {rs ? (
                              <span style={{
                                fontSize: 11, background: '#f0f9ff', color: '#0369a1',
                                padding: '2px 8px', borderRadius: 8, border: '1px solid #bae6fd',
                              }}>{rs.name}</span>
                            ) : <span style={{ color: '#d1d5db' }}>—</span>}
                          </td>
                          <td style={{ color: '#9ca3af', fontSize: 12, whiteSpace: 'nowrap' }}>
                            {new Date(p.created_at + 'Z').toLocaleDateString('ko-KR', { timeZone: 'Asia/Seoul' })}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              )}

              {/* 페이지네이션 */}
              {totalPages > 1 && (
                <div style={{
                  display: 'flex', justifyContent: 'center', alignItems: 'center',
                  gap: 4, marginTop: 16, flexWrap: 'wrap',
                }}>
                  <button
                    className="btn btn-outline"
                    disabled={currentPage === 1}
                    onClick={() => setPage(currentPage - 1)}
                    style={{ padding: '4px 10px', fontSize: 12 }}
                  >‹ 이전</button>
                  {buildPageNumbers().map((n, i) => n === '…' ? (
                    <span key={`gap-${i}`} style={{ padding: '0 6px', color: '#9ca3af' }}>…</span>
                  ) : (
                    <button
                      key={n}
                      onClick={() => setPage(n)}
                      style={{
                        minWidth: 32, padding: '4px 8px', fontSize: 12,
                        borderRadius: 6, cursor: 'pointer',
                        border: n === currentPage ? '1px solid #2563eb' : '1px solid #e5e7eb',
                        background: n === currentPage ? '#2563eb' : '#fff',
                        color: n === currentPage ? '#fff' : '#374151',
                        fontWeight: n === currentPage ? 600 : 400,
                      }}
                    >{n}</button>
                  ))}
                  <button
                    className="btn btn-outline"
                    disabled={currentPage === totalPages}
                    onClick={() => setPage(currentPage + 1)}
                    style={{ padding: '4px 10px', fontSize: 12 }}
                  >다음 ›</button>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
