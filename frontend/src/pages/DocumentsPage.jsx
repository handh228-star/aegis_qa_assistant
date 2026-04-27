import { useState, useEffect, useRef } from 'react'
import { useNavigate, useParams, Link } from 'react-router-dom'
import { api } from '../api'

const STATUS_LABEL = {
  uploaded: '업로드됨',
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
  const fileRef = useRef()
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
      const hasGenerating = data.some(d => ['tc_generating', 'tc_retrying', 'uploaded', 'parsing'].includes(d.status))
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
      await api.uploadDocument(projectId, file)
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
                      <span className={`status-badge status-${doc.status}`}>
                        {STATUS_LABEL[doc.status] || doc.status}
                        {(doc.status === 'tc_generating' || doc.status === 'uploaded') && (
                          <span style={{ marginLeft: 6 }}>⟳</span>
                        )}
                      </span>
                    </td>
                    <td style={{ color: '#9ca3af', fontSize: 12 }}>
                      {new Date(doc.created_at).toLocaleString('ko-KR')}
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
