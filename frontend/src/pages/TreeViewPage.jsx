import { useState, useEffect, useRef } from 'react'
import { useNavigate, useParams, Link } from 'react-router-dom'
import { api } from '../api'

function formatDuration(seconds) {
  if (seconds < 60) return `${seconds}초`
  return `${Math.floor(seconds / 60)}분 ${seconds % 60}초`
}

const CHANGE_TYPE_LABEL = {
  new_feature: { label: '신규', color: '#16a34a', bg: '#dcfce7' },
  modification: { label: '수정', color: '#2563eb', bg: '#dbeafe' },
  bug_fix: { label: '버그수정', color: '#dc2626', bg: '#fee2e2' },
  unknown: { label: '일반', color: '#6b7280', bg: '#f3f4f6' },
}

function countLeaves(nodes) {
  return nodes.reduce((acc, n) => {
    if (!n.children || n.children.length === 0) return acc + 1
    return acc + countLeaves(n.children)
  }, 0)
}

function collectAllIds(nodes) {
  const ids = []
  function walk(arr) {
    arr.forEach(n => { ids.push(n.id); if (n.children) walk(n.children) })
  }
  walk(nodes)
  return ids
}

function TreeNode({ node, excluded, onToggleExclude, depth = 0 }) {
  const [open, setOpen] = useState(true)
  const hasChildren = node.children && node.children.length > 0
  const isExcluded = excluded.has(node.id)
  const ct = CHANGE_TYPE_LABEL[node.change_type] || CHANGE_TYPE_LABEL.unknown

  return (
    <div style={{ marginLeft: depth * 20, marginBottom: 4 }}>
      <div style={{
        display: 'flex', alignItems: 'flex-start', gap: 8, padding: '8px 12px',
        borderRadius: 8, background: isExcluded ? '#f9fafb' : '#fff',
        border: `1px solid ${isExcluded ? '#e5e7eb' : '#d1d5db'}`,
        opacity: isExcluded ? 0.45 : 1,
      }}>
        {/* 열기/닫기 */}
        <button
          onClick={() => setOpen(o => !o)}
          style={{ background: 'none', border: 'none', cursor: hasChildren ? 'pointer' : 'default',
            color: '#9ca3af', fontSize: 12, padding: '2px 4px', minWidth: 20, flexShrink: 0 }}
        >
          {hasChildren ? (open ? '▼' : '▶') : '•'}
        </button>

        {/* 내용 */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
            <span style={{ fontWeight: depth === 0 ? 700 : depth === 1 ? 600 : 500,
              fontSize: depth === 0 ? 15 : 14, color: '#111827' }}>
              {node.name}
            </span>
            <span style={{ fontSize: 11, fontWeight: 600, padding: '1px 7px', borderRadius: 10,
              color: ct.color, background: ct.bg }}>
              {ct.label}
            </span>
          </div>
          {node.description && (
            <div style={{ fontSize: 12, color: '#6b7280', marginTop: 2 }}>{node.description}</div>
          )}
          {node.key_points && node.key_points.length > 0 && (
            <div style={{ marginTop: 4, display: 'flex', flexWrap: 'wrap', gap: 4 }}>
              {node.key_points.map((kp, i) => (
                <span key={i} style={{ fontSize: 11, background: '#f0f9ff', color: '#0369a1',
                  padding: '1px 8px', borderRadius: 10, border: '1px solid #bae6fd' }}>
                  {kp}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* 제외 토글 */}
        <button
          onClick={() => onToggleExclude(node.id)}
          title={isExcluded ? 'TC 생성에 포함' : 'TC 생성에서 제외'}
          style={{
            fontSize: 11, padding: '2px 10px', borderRadius: 6, border: '1px solid',
            cursor: 'pointer', flexShrink: 0,
            borderColor: isExcluded ? '#d1d5db' : '#ef4444',
            color: isExcluded ? '#9ca3af' : '#ef4444',
            background: '#fff',
          }}
        >
          {isExcluded ? '포함' : '제외'}
        </button>
      </div>

      {hasChildren && open && (
        <div style={{ marginTop: 4 }}>
          {node.children.map(child => (
            <TreeNode key={child.id} node={child} excluded={excluded}
              onToggleExclude={onToggleExclude} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  )
}

export default function TreeViewPage() {
  const { documentId } = useParams()
  const navigate = useNavigate()
  const [tree, setTree] = useState(null)
  const [excluded, setExcluded] = useState(new Set())
  const [generating, setGenerating] = useState(false)
  const [progress, setProgress] = useState({ current: 0, total: 0, startedAt: null, elapsed: 0 })
  const [error, setError] = useState(null)
  const pollingRef = useRef(null)
  const elapsedRef = useRef(null)

  useEffect(() => {
    loadTree()
    return () => {
      clearInterval(pollingRef.current)
      clearInterval(elapsedRef.current)
    }
  }, [documentId])

  async function loadTree() {
    try {
      const { data } = await api.getTree(documentId)
      setTree(data)
    } catch (e) {
      setError('메뉴트리를 불러올 수 없습니다.')
    }
  }

  function toggleExclude(id) {
    setExcluded(prev => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  function filterTree(nodes) {
    return nodes
      .filter(n => !excluded.has(n.id))
      .map(n => ({ ...n, children: n.children ? filterTree(n.children) : [] }))
  }

  async function handleGenerateTc() {
    setGenerating(true)
    try {
      // 제외 항목 반영한 트리 저장 후 TC 생성
      if (tree && excluded.size > 0) {
        const filtered = { ...tree, tree: filterTree(tree.tree || []) }
        await api.updateTree(documentId, filtered)
      }
      await api.generateTc(documentId)

      const startTime = Date.now()
      elapsedRef.current = setInterval(() => {
        setProgress(p => ({ ...p, elapsed: Math.floor((Date.now() - startTime) / 1000) }))
      }, 1000)

      // TC 생성 완료까지 폴링
      pollingRef.current = setInterval(async () => {
        try {
          const { data } = await api.getDocumentStatus(documentId)
          setProgress(p => ({
            ...p,
            current: data.progress_current || 0,
            total: data.progress_total || 0,
          }))
          if (data.status === 'tc_generated') {
            clearInterval(pollingRef.current)
            clearInterval(elapsedRef.current)
            navigate(`/review/${documentId}`)
          } else if (data.status === 'failed') {
            clearInterval(pollingRef.current)
            clearInterval(elapsedRef.current)
            setError('TC 생성 중 오류가 발생했습니다: ' + (data.error_message || ''))
            setGenerating(false)
          }
        } catch (e) { /* 네트워크 오류 무시 */ }
      }, 3000)
    } catch (e) {
      setError('TC 생성 시작 실패: ' + (e.response?.data?.detail || e.message))
      setGenerating(false)
    }
  }


  const totalFeatures = tree ? countLeaves(tree.tree || []) : 0
  const excludedCount = excluded.size
  const includeCount = totalFeatures - excludedCount

  return (
    <div className="page">
      <nav className="navbar">
        <Link to="/" className="navbar-brand">🛡 Aegis QA</Link>
        <span className="navbar-sep">›</span>
        <span className="navbar-item">메뉴트리 검토</span>
      </nav>

      <div className="container">
        <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h1>{tree?.title || '메뉴트리'}</h1>
            <p>AI가 기획서를 분석하여 테스트 대상 기능 구조를 추출했습니다. 검토 후 TC를 생성하세요.</p>
          </div>
          <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexShrink: 0 }}>
            <div style={{ fontSize: 13, color: '#6b7280', textAlign: 'right' }}>
              <div>전체 기능: <strong>{totalFeatures}</strong>개</div>
              {excludedCount > 0 && <div style={{ color: '#ef4444' }}>제외: {excludedCount}개</div>}
              <div style={{ color: '#16a34a' }}>생성 대상: <strong>{includeCount}</strong>개</div>
            </div>
            {tree && (
              <a
                href={api.treeExportUrl(documentId)}
                target="_blank"
                rel="noreferrer"
                style={{
                  padding: '10px 16px', borderRadius: 8, border: '1px solid #d1d5db',
                  background: '#fff', color: '#374151', fontWeight: 600, fontSize: 14,
                  textDecoration: 'none', display: 'inline-block',
                }}
              >
                📥 Excel 다운로드
              </a>
            )}
            <button
              onClick={handleGenerateTc}
              disabled={generating || includeCount === 0}
              style={{
                padding: '10px 24px', borderRadius: 8, border: 'none',
                background: generating ? '#9ca3af' : '#2563eb',
                color: '#fff', fontWeight: 700, fontSize: 15, cursor: generating ? 'not-allowed' : 'pointer',
              }}
            >
              {generating ? (
                <span>TC 생성중 ⟳</span>
              ) : (
                <span>TC 생성 시작 →</span>
              )}
            </button>
          </div>
        </div>

        {error && (
          <div style={{ padding: 12, background: '#fee2e2', borderRadius: 8, color: '#dc2626',
            marginBottom: 16, fontSize: 14 }}>
            {error}
          </div>
        )}

        {generating && (
          <div style={{ padding: 16, background: '#eff6ff', borderRadius: 8, marginBottom: 16 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
              <div className="spinner" style={{ width: 18, height: 18, borderTopColor: '#2563eb',
                borderColor: '#bfdbfe', flexShrink: 0 }} />
              <span style={{ fontSize: 14, color: '#2563eb', fontWeight: 600 }}>TC 생성 중</span>
              <span style={{ fontSize: 13, color: '#6b7280', marginLeft: 'auto' }}>
                {progress.elapsed > 0 && `${formatDuration(progress.elapsed)} 경과`}
              </span>
            </div>
            {progress.total > 0 ? (
              <>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: '#374151', marginBottom: 4 }}>
                  <span>기능 <strong>{progress.current}</strong> / {progress.total} 처리 중</span>
                  <span>{Math.round((progress.current / progress.total) * 100)}%</span>
                </div>
                <div style={{ height: 8, background: '#bfdbfe', borderRadius: 4, overflow: 'hidden' }}>
                  <div style={{
                    height: '100%', background: '#2563eb', borderRadius: 4,
                    width: `${Math.round((progress.current / progress.total) * 100)}%`,
                    transition: 'width 0.5s ease',
                  }} />
                </div>
                {progress.current > 0 && progress.elapsed > 0 && (
                  <div style={{ fontSize: 11, color: '#6b7280', marginTop: 4, textAlign: 'right' }}>
                    약 {formatDuration(Math.round((progress.elapsed / progress.current) * (progress.total - progress.current)))} 남음
                  </div>
                )}
              </>
            ) : (
              <div style={{ fontSize: 13, color: '#6b7280' }}>기능 목록 준비 중...</div>
            )}
          </div>
        )}

        <div className="card">
          <div style={{ marginBottom: 12, display: 'flex', gap: 16, fontSize: 12, color: '#6b7280' }}>
            <span>▼/▶ 클릭으로 접기/펼치기</span>
            <span>|</span>
            <span>제외 버튼으로 TC 생성 범위 조정</span>
            {excludedCount > 0 && (
              <>
                <span>|</span>
                <button onClick={() => setExcluded(new Set())}
                  style={{ background: 'none', border: 'none', color: '#2563eb', cursor: 'pointer',
                    fontSize: 12, padding: 0 }}>
                  제외 모두 해제
                </button>
              </>
            )}
          </div>

          {tree ? (
            <div>
              {(tree.tree || []).map(node => (
                <TreeNode key={node.id} node={node} excluded={excluded}
                  onToggleExclude={toggleExclude} depth={0} />
              ))}
            </div>
          ) : !error ? (
            <div className="empty">
              <div className="spinner" style={{ width: 32, height: 32, borderTopColor: '#2563eb',
                borderColor: '#e5e7eb', margin: '0 auto 12px' }} />
              <p>메뉴트리를 불러오는 중...</p>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  )
}
