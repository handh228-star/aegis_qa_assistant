import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'

function RuleSetForm({ initial, onSave, onCancel }) {
  const [form, setForm] = useState(initial || {
    name: '', description: '', service_type: '', tree_rules: '', tc_rules: '',
  })
  const [saving, setSaving] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    if (!form.name.trim()) return
    setSaving(true)
    try { await onSave(form) } finally { setSaving(false) }
  }

  return (
    <form onSubmit={handleSubmit} style={{ background: '#f9fafb', borderRadius: 10, padding: 20, marginBottom: 20 }}>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 12 }}>
        <div className="form-group" style={{ margin: 0 }}>
          <label>룰셋 이름 *</label>
          <input value={form.name} onChange={e => setForm({ ...form, name: e.target.value })}
            placeholder="예: ERP 공통, 쇼핑몰 특화" autoFocus />
        </div>
        <div className="form-group" style={{ margin: 0 }}>
          <label>서비스 유형</label>
          <input value={form.service_type} onChange={e => setForm({ ...form, service_type: e.target.value })}
            placeholder="예: ERP, 쇼핑몰, 모바일앱, 공통" />
        </div>
      </div>
      <div className="form-group">
        <label>설명</label>
        <input value={form.description} onChange={e => setForm({ ...form, description: e.target.value })}
          placeholder="이 룰셋의 특징 및 적용 대상 설명" />
      </div>
      <div className="form-group">
        <label>메뉴트리 추출 지침</label>
        <textarea
          value={form.tree_rules}
          onChange={e => setForm({ ...form, tree_rules: e.target.value })}
          rows={8}
          placeholder="메뉴트리를 어떤 기준으로 추출할지 AI에게 추가로 지시할 내용..."
          style={{ fontFamily: 'monospace', fontSize: 13 }}
        />
      </div>
      <div className="form-group">
        <label>TC 생성 지침</label>
        <textarea
          value={form.tc_rules}
          onChange={e => setForm({ ...form, tc_rules: e.target.value })}
          rows={10}
          placeholder="TC를 어떤 기준으로 생성할지 AI에게 추가로 지시할 내용..."
          style={{ fontFamily: 'monospace', fontSize: 13 }}
        />
      </div>
      <div style={{ display: 'flex', gap: 8 }}>
        <button type="submit" className="btn btn-primary" disabled={saving}>
          {saving ? '저장중...' : '저장'}
        </button>
        <button type="button" className="btn btn-outline" onClick={onCancel}>취소</button>
      </div>
    </form>
  )
}

export default function RulesetsPage() {
  const [rulesets, setRulesets] = useState([])
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState(null)
  const [collapsedIds, setCollapsedIds] = useState(new Set())

  useEffect(() => { load() }, [])

  async function load() {
    try {
      const { data } = await api.getRulesets()
      setRulesets(data)
    } catch (e) { console.error(e) }
  }

  async function handleCreate(form) {
    await api.createRuleset(form)
    setShowForm(false)
    load()
  }

  async function handleUpdate(id, form) {
    await api.updateRuleset(id, form)
    setEditing(null)
    load()
  }

  async function handleSetDefault(id) {
    await api.updateRuleset(id, { is_default: true })
    load()
  }

  async function handleDelete(id, name) {
    if (!confirm(`'${name}' 룰셋을 삭제할까요?`)) return
    try {
      await api.deleteRuleset(id)
      load()
    } catch (e) {
      alert(e.response?.data?.detail || '삭제 실패')
    }
  }

  return (
    <div className="page">
      <nav className="navbar">
        <Link to="/" className="navbar-brand">🛡 Aegis QA</Link>
        <span className="navbar-sep">›</span>
        <span className="navbar-item">QA 룰셋 관리</span>
      </nav>

      <div className="container">
        <div className="page-header">
          <div>
            <h1>QA 룰셋 관리</h1>
            <p>메뉴트리 추출 및 TC 생성 시 AI에게 적용할 규칙을 정의합니다. 프로젝트 생성 시 룰셋을 선택할 수 있습니다.</p>
          </div>
          <button className="btn btn-primary" onClick={() => { setShowForm(true); setEditing(null) }}>
            + 새 룰셋
          </button>
        </div>

        {showForm && !editing && (
          <div className="card">
            <div className="card-header"><span className="card-title">새 룰셋 만들기</span></div>
            <RuleSetForm onSave={handleCreate} onCancel={() => setShowForm(false)} />
          </div>
        )}

        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {rulesets.map(rs => (
            <div key={rs.id} className="card" style={{ padding: 0, overflow: 'hidden' }}>
              {editing === rs.id ? (
                <div style={{ padding: 20 }}>
                  <div className="card-header" style={{ marginBottom: 12, padding: 0 }}>
                    <span className="card-title">룰셋 수정</span>
                  </div>
                  <RuleSetForm
                    initial={rs}
                    onSave={(form) => handleUpdate(rs.id, form)}
                    onCancel={() => setEditing(null)}
                  />
                </div>
              ) : (
                <>
                  <div style={{ padding: '16px 20px', display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                        <span style={{ fontWeight: 700, fontSize: 15 }}>{rs.name}</span>
                        {rs.is_default && (
                          <span style={{ fontSize: 11, background: '#dbeafe', color: '#2563eb',
                            padding: '2px 8px', borderRadius: 10, fontWeight: 600 }}>기본값</span>
                        )}
                        {rs.is_system && (
                          <span style={{ fontSize: 11, background: '#f3f4f6', color: '#6b7280',
                            padding: '2px 8px', borderRadius: 10 }}>시스템</span>
                        )}
                        {rs.service_type && (
                          <span style={{ fontSize: 11, background: '#fef3c7', color: '#92400e',
                            padding: '2px 8px', borderRadius: 10 }}>{rs.service_type}</span>
                        )}
                      </div>
                      {rs.description && (
                        <div style={{ fontSize: 13, color: '#6b7280', marginTop: 3 }}>{rs.description}</div>
                      )}
                    </div>
                    <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
                      <button
                        onClick={() => setCollapsedIds(prev => {
                          const next = new Set(prev)
                          next.has(rs.id) ? next.delete(rs.id) : next.add(rs.id)
                          return next
                        })}
                        style={{ fontSize: 12, padding: '4px 12px', borderRadius: 6, border: '1px solid #d1d5db',
                          background: '#fff', cursor: 'pointer', color: '#374151' }}
                      >
                        {collapsedIds.has(rs.id) ? '내용보기' : '접기'}
                      </button>
                      {!rs.is_default && (
                        <button onClick={() => handleSetDefault(rs.id)}
                          style={{ fontSize: 12, padding: '4px 12px', borderRadius: 6, border: '1px solid #bfdbfe',
                            background: '#eff6ff', cursor: 'pointer', color: '#2563eb' }}>
                          기본값 설정
                        </button>
                      )}
                      <button onClick={() => { setEditing(rs.id); setShowForm(false) }}
                        style={{ fontSize: 12, padding: '4px 12px', borderRadius: 6, border: '1px solid #d1d5db',
                          background: '#fff', cursor: 'pointer', color: '#374151' }}>
                        수정
                      </button>
                      {!rs.is_system && (
                        <button onClick={() => handleDelete(rs.id, rs.name)}
                          style={{ fontSize: 12, padding: '4px 12px', borderRadius: 6, border: '1px solid #fecaca',
                            background: '#fff', cursor: 'pointer', color: '#ef4444' }}>
                          삭제
                        </button>
                      )}
                    </div>
                  </div>

                  {!collapsedIds.has(rs.id) && (
                    <div style={{ borderTop: '1px solid #f3f4f6', padding: '16px 20px', background: '#fafafa' }}>
                      {rs.tree_rules && (
                        <div style={{ marginBottom: 16 }}>
                          <div style={{ fontSize: 12, fontWeight: 600, color: '#374151', marginBottom: 6 }}>
                            메뉴트리 추출 지침
                          </div>
                          <pre style={{ fontSize: 12, color: '#4b5563', whiteSpace: 'pre-wrap',
                            background: '#f3f4f6', padding: 12, borderRadius: 6, margin: 0, lineHeight: 1.6 }}>
                            {rs.tree_rules}
                          </pre>
                        </div>
                      )}
                      {rs.tc_rules && (
                        <div>
                          <div style={{ fontSize: 12, fontWeight: 600, color: '#374151', marginBottom: 6 }}>
                            TC 생성 지침
                          </div>
                          <pre style={{ fontSize: 12, color: '#4b5563', whiteSpace: 'pre-wrap',
                            background: '#f3f4f6', padding: 12, borderRadius: 6, margin: 0, lineHeight: 1.6 }}>
                            {rs.tc_rules}
                          </pre>
                        </div>
                      )}
                    </div>
                  )}
                </>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
