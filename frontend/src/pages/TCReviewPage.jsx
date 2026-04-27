import { useState, useEffect } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { api } from '../api'

const TYPE_LABEL = { positive: '정상', negative: '비정상', boundary: '경계값', exception: '예외' }
const PRIORITY_LABEL = { high: 'HIGH', medium: 'MED', low: 'LOW' }
const REVIEW_LABEL = { pending: '대기', approved: '승인', needs_revision: '수정요청', admin_required: '관리자확인', deleted: '삭제' }

function ReviewModal({ tc, onClose, onSave }) {
  const [note, setNote] = useState(tc?.review_note || '')
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <h3>✏️ 수정 요청</h3>
        <p className="tc-ref" style={{ color: '#6b7280', marginBottom: 12 }}>
          {tc?.tc_id} · {tc?.title}
        </p>
        <textarea
          value={note}
          onChange={e => setNote(e.target.value)}
          placeholder="수정이 필요한 내용을 구체적으로 입력하세요&#10;예) 비정상 케이스 추가 필요 / 스텝이 너무 단순함 / 경계값 케이스로 변경해주세요"
          autoFocus
        />
        <div className="modal-footer">
          <button className="btn btn-outline" onClick={onClose}>취소</button>
          <button className="btn btn-warning" onClick={() => onSave(note)}>수정요청 저장</button>
        </div>
      </div>
    </div>
  )
}

function TCRow({ tc, expanded, onToggle, onApprove, onRevise, onAdmin, onDelete }) {
  return (
    <>
      <tr className={`tc-row ${expanded ? 'expanded' : ''}`} onClick={onToggle}>
        <td style={{ color: '#9ca3af', fontFamily: 'monospace', fontSize: 12 }}>{tc.tc_id}</td>
        <td style={{ maxWidth: 140, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          <span title={tc.category}>{tc.category}</span>
        </td>
        <td style={{ maxWidth: 280 }}>
          <span style={{ fontWeight: 500 }}>{tc.title}</span>
        </td>
        <td><span className={`badge badge-${tc.tc_type}`}>{TYPE_LABEL[tc.tc_type]}</span></td>
        <td><span className={`badge badge-${tc.priority}`}>{PRIORITY_LABEL[tc.priority]}</span></td>
        <td><span className={`badge badge-${tc.review_status}`}>{REVIEW_LABEL[tc.review_status]}</span></td>
        <td onClick={e => e.stopPropagation()}>
          <div className="action-btns">
            <button
              className="action-btn action-approve"
              title="승인"
              onClick={() => onApprove(tc)}
            >✓</button>
            <button
              className="action-btn action-revise"
              title="수정 요청"
              onClick={() => onRevise(tc)}
            >✏️</button>
            <button
              className="action-btn action-admin"
              title="관리자 확인 필요"
              onClick={() => onAdmin(tc)}
            >👑</button>
            <button
              className="action-btn action-delete"
              title="삭제"
              onClick={() => onDelete(tc)}
            >✗</button>
          </div>
        </td>
      </tr>
      {expanded && (
        <tr className="tc-detail">
          <td colSpan={7}>
            <div className="detail-grid">
              <div>
                <div className="detail-section" style={{ marginBottom: 14 }}>
                  <h4>목적</h4>
                  <p>{tc.objective}</p>
                </div>
                {tc.preconditions?.length > 0 && (
                  <div className="detail-section">
                    <h4>사전조건</h4>
                    <ul className="preconditions-list">
                      {tc.preconditions.map((p, i) => <li key={i}>{p}</li>)}
                    </ul>
                  </div>
                )}
              </div>
              <div>
                <div className="detail-section" style={{ marginBottom: 14 }}>
                  <h4>테스트 단계</h4>
                  <ul className="steps-list">
                    {(tc.steps || []).map((s, i) => (
                      <li key={i}>
                        <span className="step-num">{s.step || i + 1}</span>
                        <div className="step-content">
                          <div className="action">{s.action}</div>
                          {s.expected && <div className="expected">→ {s.expected}</div>}
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
                <div className="detail-section">
                  <h4>최종 기대 결과</h4>
                  <p>{tc.expected_result}</p>
                </div>
              </div>
            </div>
            {tc.review_note && (
              <div className="review-note-box" style={{ marginTop: 12 }}>
                💬 수정 요청: {tc.review_note}
              </div>
            )}
          </td>
        </tr>
      )}
    </>
  )
}

export default function TCReviewPage() {
  const { documentId } = useParams()
  const navigate = useNavigate()
  const [tcs, setTcs] = useState([])
  const [summary, setSummary] = useState(null)
  const [, setDocument] = useState(null)
  const [filters, setFilters] = useState({ tc_type: '', priority: '', review_status: '' })
  const [expandedId, setExpandedId] = useState(null)
  const [modalTc, setModalTc] = useState(null)
  const [isRegenerating, setIsRegenerating] = useState(false)

  useEffect(() => { loadAll() }, [documentId])

  async function loadAll() {
    try {
      const [tcRes, sumRes, docRes] = await Promise.all([
        api.getTestcases(documentId),
        api.getSummary(documentId),
        api.getDocumentStatus(documentId),
      ])
      setTcs(tcRes.data)
      setSummary(sumRes.data)
      setDocument(docRes.data)
    } catch (e) { console.error(e) }
  }

  async function loadTcs() {
    try {
      const { data } = await api.getTestcases(documentId)
      setTcs(data)
      const { data: sum } = await api.getSummary(documentId)
      setSummary(sum)
    } catch (e) { console.error(e) }
  }

  async function handleApprove(tc) {
    // 이미 승인 상태면 대기로 토글
    const newStatus = tc.review_status === 'approved' ? 'pending' : 'approved'
    await api.reviewTc(tc.id, newStatus, null)
    loadTcs()
  }

  async function handleRevise(tc) {
    setModalTc(tc)
  }

  async function handleModalSave(note) {
    await api.reviewTc(modalTc.id, 'needs_revision', note)
    setModalTc(null)
    loadTcs()
  }

  async function handleAdmin(tc) {
    const newStatus = tc.review_status === 'admin_required' ? 'pending' : 'admin_required'
    await api.reviewTc(tc.id, newStatus, tc.review_note || null)
    loadTcs()
  }

  async function handleDelete(tc) {
    if (!confirm(`"${tc.title}" TC를 삭제하시겠습니까?`)) return
    await api.deleteTc(tc.id)
    setExpandedId(null)
    loadTcs()
  }

  async function handleRegenerate() {
    const revisionCount = tcs.filter(t => t.review_status === 'needs_revision').length
    if (revisionCount === 0) {
      alert('수정 요청된 TC가 없습니다. ✏️ 버튼으로 수정 요청 후 사용하세요.')
      return
    }
    if (!confirm(`수정 요청된 TC ${revisionCount}개를 AI가 재생성합니다. 계속하시겠습니까?`)) return
    setIsRegenerating(true)
    try {
      const { data } = await api.regenerate(documentId)
      alert(`✅ ${data.regenerated}개 TC가 재생성되었습니다`)
      loadTcs()
    } catch (e) {
      alert('재생성 실패: ' + (e.response?.data?.detail || e.message))
    } finally {
      setIsRegenerating(false)
    }
  }

  // 필터 적용
  const filtered = tcs.filter(tc => {
    if (filters.tc_type && tc.tc_type !== filters.tc_type) return false
    if (filters.priority && tc.priority !== filters.priority) return false
    if (filters.review_status && tc.review_status !== filters.review_status) return false
    return true
  })

  const revisionCount = tcs.filter(t => t.review_status === 'needs_revision').length
  const rd = summary?.review_distribution || {}

  function FilterChip({ field, value, label }) {
    const active = filters[field] === value
    return (
      <button
        className={`filter-chip ${active ? 'active' : ''}`}
        onClick={() => setFilters(f => ({ ...f, [field]: active ? '' : value }))}
      >
        {label}
      </button>
    )
  }

  return (
    <div className="page">
      <nav className="navbar">
        <Link to="/" className="navbar-brand">🛡 Aegis QA</Link>
        <span className="navbar-sep">›</span>
        <span className="navbar-item" style={{ cursor: 'pointer' }} onClick={() => navigate(-1)}>
          문서 목록
        </span>
        <span className="navbar-sep">›</span>
        <span className="navbar-item">TC 검토</span>
      </nav>

      <div className="container">
        <div className="page-header">
          <h1>TC 검토</h1>
          <p>TC를 승인하거나 수정 요청한 후 AI 보완 요청을 실행하세요</p>
        </div>

        {/* 통계 */}
        <div className="stats-bar">
          <div className="stat-box">
            <div className="stat-num">{summary?.total || 0}</div>
            <div className="stat-label">전체</div>
          </div>
          <div className="stat-box stat-pending">
            <div className="stat-num">{rd.pending || 0}</div>
            <div className="stat-label">검토 대기</div>
          </div>
          <div className="stat-box stat-approved">
            <div className="stat-num">{rd.approved || 0}</div>
            <div className="stat-label">승인 ✓</div>
          </div>
          <div className="stat-box stat-revision">
            <div className="stat-num">{rd.needs_revision || 0}</div>
            <div className="stat-label">수정 요청 ✏️</div>
          </div>
          <div className="stat-box stat-admin">
            <div className="stat-num">{rd.admin_required || 0}</div>
            <div className="stat-label">관리자확인 👑</div>
          </div>
          <div className="stat-box stat-deleted">
            <div className="stat-num">{rd.deleted || 0}</div>
            <div className="stat-label">삭제 예정 ✗</div>
          </div>
          {summary?.type_distribution && Object.entries(summary.type_distribution).map(([k, v]) => (
            <div key={k} className="stat-box">
              <div className="stat-num" style={{ fontSize: 18 }}>{v}</div>
              <div className="stat-label">{TYPE_LABEL[k] || k}</div>
            </div>
          ))}
        </div>

        {/* 필터 */}
        <div className="filters">
          <span className="filter-label">유형</span>
          {['positive', 'negative', 'boundary', 'exception'].map(t => (
            <FilterChip key={t} field="tc_type" value={t} label={TYPE_LABEL[t]} />
          ))}
          <div className="filter-sep" />
          <span className="filter-label">우선순위</span>
          {['high', 'medium', 'low'].map(p => (
            <FilterChip key={p} field="priority" value={p} label={PRIORITY_LABEL[p]} />
          ))}
          <div className="filter-sep" />
          <span className="filter-label">검토</span>
          {['pending', 'approved', 'needs_revision', 'admin_required', 'deleted'].map(r => (
            <FilterChip key={r} field="review_status" value={r} label={REVIEW_LABEL[r]} />
          ))}
        </div>

        {/* TC 테이블 */}
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <table className="tc-table">
            <thead>
              <tr>
                <th>TC ID</th>
                <th>카테고리</th>
                <th>제목</th>
                <th>유형</th>
                <th>우선순위</th>
                <th>검토상태</th>
                <th>액션</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={7} style={{ textAlign: 'center', padding: '40px', color: '#9ca3af' }}>
                    TC가 없습니다
                  </td>
                </tr>
              ) : (
                filtered.map(tc => (
                  <TCRow
                    key={tc.id}
                    tc={tc}
                    expanded={expandedId === tc.id}
                    onToggle={() => setExpandedId(expandedId === tc.id ? null : tc.id)}
                    onApprove={handleApprove}
                    onRevise={handleRevise}
                    onAdmin={handleAdmin}
                    onDelete={handleDelete}
                  />
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* 하단 액션 */}
        <div className="bottom-actions">
          <div style={{ fontSize: 13, color: '#6b7280' }}>
            {filtered.length}개 표시 / 전체 {tcs.length}개
          </div>
          <div style={{ display: 'flex', gap: 10 }}>
            <button
              className="btn btn-warning"
              onClick={handleRegenerate}
              disabled={isRegenerating || revisionCount === 0}
            >
              {isRegenerating ? (
                <><span className="spinner" /> AI 재생성 중...</>
              ) : (
                `🤖 AI 보완 요청 ${revisionCount > 0 ? `(${revisionCount}건)` : ''}`
              )}
            </button>
            <a
              href={api.exportUrl(documentId)}
              target="_blank"
              rel="noreferrer"
              className="btn btn-success"
            >
              📥 Excel 다운로드
            </a>
          </div>
        </div>
      </div>

      {modalTc && (
        <ReviewModal
          tc={modalTc}
          onClose={() => setModalTc(null)}
          onSave={handleModalSave}
        />
      )}
    </div>
  )
}
