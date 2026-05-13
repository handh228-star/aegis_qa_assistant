import { useState, useEffect, useRef, useCallback } from 'react'
import { useNavigate, useParams, Link } from 'react-router-dom'
import { api } from '../api'

function useElapsed(startedAt) {
  const [elapsed, setElapsed] = useState(0)
  useEffect(() => {
    if (!startedAt) return
    const start = new Date(startedAt + 'Z').getTime()
    const tick = () => setElapsed(Math.floor((Date.now() - start) / 1000))
    tick()
    const id = setInterval(tick, 1000)
    return () => clearInterval(id)
  }, [startedAt])
  return elapsed
}

function formatDuration(seconds) {
  if (seconds < 60) return `${seconds}초`
  return `${Math.floor(seconds / 60)}분 ${seconds % 60}초`
}

function ProgressCell({ doc }) {
  const elapsed = useElapsed(
    ['tc_generating', 'tc_retrying'].includes(doc.status) ? doc.tc_started_at : null
  )
  const cur = doc.progress_current || 0
  const total = doc.progress_total || 0
  const pct = total > 0 ? Math.round((cur / total) * 100) : 0

  if (!['tc_generating', 'tc_retrying'].includes(doc.status)) {
    return (
      <span className={`status-badge status-${doc.status}`}>
        {STATUS_LABEL[doc.status] || doc.status}
        {['uploaded', 'analyzing'].includes(doc.status) && <span style={{ marginLeft: 6 }}>⟳</span>}
      </span>
    )
  }

  const eta = cur > 0 && elapsed > 0
    ? formatDuration(Math.round((elapsed / cur) * (total - cur)))
    : null

  return (
    <div style={{ minWidth: 160 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: '#6b7280', marginBottom: 3 }}>
        <span style={{ color: '#2563eb', fontWeight: 600 }}>
          TC 생성중 {cur > 0 && total > 0 ? `${cur}/${total}` : ''}
        </span>
        <span>{elapsed > 0 ? formatDuration(elapsed) + ' 경과' : ''}</span>
      </div>
      <div style={{ height: 6, background: '#e5e7eb', borderRadius: 3, overflow: 'hidden' }}>
        <div style={{
          height: '100%', borderRadius: 3,
          background: pct > 0 ? '#2563eb' : '#93c5fd',
          width: pct > 0 ? `${pct}%` : '100%',
          transition: 'width 0.5s ease',
          animation: pct === 0 ? 'pulse 1.5s ease-in-out infinite' : 'none',
        }} />
      </div>
      {pct > 0 && (
        <div style={{ fontSize: 10, color: '#9ca3af', marginTop: 2, display: 'flex', justifyContent: 'space-between' }}>
          <span>{pct}%</span>
          {eta && <span>약 {eta} 남음</span>}
        </div>
      )}
    </div>
  )
}

const STATUS_LABEL = {
  uploaded: '업로드됨',
  analyzing: '트리 생성중',
  analyzed: '트리 검토 필요',
  parsing: '분석중',
  parsed: '분석완료',
  tc_generating: 'TC 생성중',
  tc_retrying: 'TC 재시도중',
  tc_generated: 'TC 완료',
  failed: '실패',
}

export default function DocumentsPage() {
  const { projectId } = useParams()
  const [project, setProject] = useState(null)
  const [documents, setDocuments] = useState([])
  const [uploading, setUploading] = useState(false)
  const [tcLevel, setTcLevel] = useState(3)
  const fileRef = useRef()

  const LEVEL_INFO = {
    1: { label: '핵심 검증', desc: '대표 케이스 위주, 리스크가 낮거나 일정이 촉박한 경우' },
    2: { label: '표준 검증', desc: '정상/비정상/경계값/예외 균형 있게, 일반 프로젝트에 적합' },
    3: { label: '정밀 검증', desc: '세부 시나리오·업무 규칙 예외 포함, 중요도 높은 기능에 권장' },
    4: { label: '심층 검증', desc: '조합 케이스·연동 시나리오까지, 고품질 검증이 필요한 경우' },
    5: { label: '전수 검증', desc: '모든 엣지케이스 망라, 대형 릴리즈·고위험 프로젝트' },
  }
  const navigate = useNavigate()
  const pollingRef = useRef(null)

  useEffect(() => {
    loadProject()
    loadDocuments()
    return () => clearInterval(pollingRef.current)
  }, [projectId])

  async function loadProject() {
    try {
      const { data } = await api.getProject(projectId)
      setProject(data)
    } catch (e) { console.error(e) }
  }

  async function loadDocuments() {
    try {
      const { data } = await api.getDocuments(projectId)
      setDocuments(data)
      // 생성 중인 문서가 있으면 폴링
      const hasGenerating = data.some(d => ['tc_generating', 'tc_retrying', 'uploaded', 'parsing', 'analyzing'].includes(d.status))
      if (hasGenerating) {
        clearInterval(pollingRef.current)
        pollingRef.current = setInterval(loadDocuments, 3000)
      } else {
        clearInterval(pollingRef.current)
      }
    } catch (e) { console.error(e) }
  }

  async function handleUpload(file) {
    if (!file || !file.name.endsWith('.pdf')) {
      alert('PDF 파일만 업로드 가능합니다')
      return
    }
    setUploading(true)
    try {
      await api.uploadDocument(projectId, file, tcLevel)
      loadDocuments()
    } catch (e) {
      alert('업로드 실패: ' + (e.response?.data?.detail || e.message))
    } finally {
      setUploading(false)
    }
  }

  function handleFileDrop(e) {
    e.preventDefault()
    const file = e.dataTransfer.files[0]
    if (file) handleUpload(file)
  }

  function handleDocClick(doc) {
    if (doc.status === 'tc_generated') {
      navigate(`/review/${doc.id}`)
    } else if (doc.status === 'analyzed') {
      navigate(`/tree/${doc.id}`)
    }
  }

  return (
    <div className="page">
      <nav className="navbar">
        <Link to="/" className="navbar-brand">🛡 Aegis QA</Link>
        <span className="navbar-sep">›</span>
        <span className="navbar-item">{project?.name || '...'}</span>
      </nav>
      <div className="container">
        <div className="page-header">
          <h1>{project?.name || '프로젝트'}</h1>
          <p>기획서 PDF를 업로드하면 AI가 테스트케이스를 자동 생성합니다</p>
        </div>

        {/* 레벨 선택 */}
        <div className="card" style={{ marginBottom: 12 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
            <span style={{ fontSize: 13, fontWeight: 600, color: '#374151', whiteSpace: 'nowrap' }}>TC 생성 레벨</span>
            <div style={{ display: 'flex', gap: 6 }}>
              {[1, 2, 3, 4, 5].map(lv => (
                <button
                  key={lv}
                  onClick={() => setTcLevel(lv)}
                  style={{
                    width: 36, height: 36, borderRadius: 8, border: '1.5px solid',
                    borderColor: tcLevel === lv ? '#2563eb' : '#d1d5db',
                    background: tcLevel === lv ? '#2563eb' : '#fff',
                    color: tcLevel === lv ? '#fff' : '#6b7280',
                    fontWeight: 700, fontSize: 14, cursor: 'pointer',
                  }}
                >{lv}</button>
              ))}
            </div>
            <span style={{ fontSize: 13, color: '#6b7280' }}>
              <span style={{ color: '#111827', fontWeight: 500 }}>{LEVEL_INFO[tcLevel].label}</span>
              {' · '}{LEVEL_INFO[tcLevel].desc}
            </span>
          </div>
        </div>

        <div className="card">
          <label
            className="upload-area"
            onDragOver={e => e.preventDefault()}
            onDrop={handleFileDrop}
          >
            <input ref={fileRef} type="file" accept=".pdf" onChange={e => handleUpload(e.target.files[0])} />
            {uploading ? (
              <div>
                <div className="spinner" style={{ borderTopColor: '#2563eb', borderColor: '#e5e7eb', width: 24, height: 24, margin: '0 auto 8px' }} />
                <p style={{ color: '#6b7280' }}>업로드 중...</p>
              </div>
            ) : (
              <div>
                <div style={{ fontSize: 36, marginBottom: 8 }}>📄</div>
                <p style={{ fontWeight: 500 }}>기획서 PDF 업로드</p>
                <p style={{ color: '#9ca3af', fontSize: 12, marginTop: 4 }}>클릭하거나 파일을 여기에 드래그하세요</p>
              </div>
            )}
          </label>
        </div>

        <div className="card">
          <div className="card-header">
            <span className="card-title">기획서 목록</span>
            <span style={{ fontSize: 12, color: '#9ca3af' }}>TC 완료된 문서를 클릭하면 검토 화면으로 이동합니다</span>
          </div>

          {documents.length === 0 ? (
            <div className="empty">
              <div style={{ fontSize: 40 }}>📋</div>
              <p>업로드된 기획서가 없습니다</p>
            </div>
          ) : (
            <table className="tc-table">
              <thead>
                <tr>
                  <th>파일명</th>
                  <th>페이지</th>
                  <th>레벨</th>
                  <th>상태</th>
                  <th>업로드일</th>
                </tr>
              </thead>
              <tbody>
                {documents.map(doc => (
                  <tr
                    key={doc.id}
                    className={`tc-row ${doc.status === 'tc_generated' ? '' : ''}`}
                    onClick={() => handleDocClick(doc)}
                    style={{ opacity: doc.status === 'tc_generated' ? 1 : 0.7 }}
                  >
                    <td>
                      <span style={{ fontWeight: 500 }}>{doc.original_filename}</span>
                    </td>
                    <td>{doc.total_pages}p</td>
                    <td>
                      <span style={{ fontSize: 12, color: '#6b7280' }}>
                        Lv.{doc.tc_level || 2} {LEVEL_INFO[doc.tc_level || 2]?.label}
                      </span>
                    </td>
                    <td>
                      <ProgressCell doc={doc} />
                    </td>
                    <td style={{ color: '#9ca3af', fontSize: 12 }}>
                      {new Date(doc.created_at + 'Z').toLocaleString('ko-KR', { timeZone: 'Asia/Seoul' })}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  )
}
