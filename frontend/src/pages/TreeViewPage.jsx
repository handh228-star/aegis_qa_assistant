import { useState, useEffect, useRef } from 'react'
import { useNavigate, useParams, Link } from 'react-router-dom'
import { api } from '../api'

function formatDuration(seconds) {
  if (seconds < 60) return `${seconds}초`
  return `${Math.floor(seconds / 60)}분 ${seconds % 60}초`
}

// 변경유형(change_type)은 트리뷰에서 시각적 노이즈가 커서 표시하지 않음.
// 데이터는 그대로 유지되어 TCReviewPage 필터·Excel 리포트·TC 생성 전략 분기에는 적용됨.

function countLeaves(nodes) {
  return nodes.reduce((acc, n) => {
    if (!n.children || n.children.length === 0) return acc + 1
    return acc + countLeaves(n.children)
  }, 0)
}

function TreeNode({ node, excluded, onToggleExclude, depth = 0 }) {
  const [open, setOpen] = useState(true)
  const hasChildren = node.children && node.children.length > 0
  const isExcluded = excluded.has(node.id)

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
          <span style={{ fontWeight: depth === 0 ? 700 : depth === 1 ? 600 : 500,
            fontSize: depth === 0 ? 15 : 14, color: '#111827' }}>
            {node.name}
          </span>
          {node.spec_page && (
            <span title={`기획서 페이지: ${node.spec_page}`}
              style={{ marginLeft: 8, fontSize: 11, color: '#6b7280', background: '#f3f4f6',
                padding: '1px 7px', borderRadius: 10, border: '1px solid #e5e7eb', verticalAlign: 'middle' }}>
              p.{node.spec_page}
            </span>
          )}
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

const FLOW_TYPE_STYLE = {
  PR: { bg: '#fef3c7', fg: '#92400e' },
  C:  { bg: '#dbeafe', fg: '#1e40af' },
  D:  { bg: '#dcfce7', fg: '#166534' },
  T:  { bg: '#fae8ff', fg: '#86198f' },
  H:  { bg: '#e0e7ff', fg: '#3730a3' },
  V:  { bg: '#fee2e2', fg: '#991b1b' },
  DC: { bg: '#dbeafe', fg: '#1e40af' },
  RC: { bg: '#dbeafe', fg: '#1e40af' },
  DD: { bg: '#dbeafe', fg: '#1e40af' },
}

function FlowNode({ node, depth = 0 }) {
  const s = FLOW_TYPE_STYLE[node.type] || { bg: '#f3f4f6', fg: '#374151' }
  const children = node.children || []
  return (
    <div style={{ marginLeft: depth ? 18 : 0, marginBottom: 3 }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
        <span style={{ flexShrink: 0, fontSize: 10, fontWeight: 700, color: s.fg, background: s.bg,
          padding: '1px 6px', borderRadius: 4, minWidth: 26, textAlign: 'center' }}>
          {node.type || '?'}
        </span>
        <span style={{ fontSize: 13, color: '#111827', lineHeight: 1.5 }}>
          {node.content}
          {node.menu_path && <span style={{ fontSize: 11, color: '#6b7280' }}> · {node.menu_path}</span>}
          {node.spec_page && <span style={{ fontSize: 10, color: '#6366f1', marginLeft: 6 }}>p.{node.spec_page}</span>}
        </span>
      </div>
      {children.length > 0 && (
        <div style={{ marginTop: 3, borderLeft: '1px solid #e5e7eb', paddingLeft: 6 }}>
          {children.map((ch, i) => <FlowNode key={ch.id || i} node={ch} depth={depth + 1} />)}
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
  const [flow, setFlow] = useState(null)       // { flow_tree, stats } | null
  const [flowBusy, setFlowBusy] = useState(false)
  const [flowMsg, setFlowMsg] = useState('')
  const [view, setView] = useState('flow')     // 'flow'(마스터) | 'structural'
  const pollingRef = useRef(null)
  const elapsedRef = useRef(null)
  const flowPollRef = useRef(null)

  useEffect(() => {
    loadTree()
    loadFlow()
    return () => {
      clearInterval(pollingRef.current)
      clearInterval(elapsedRef.current)
      clearInterval(flowPollRef.current)
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

  async function loadFlow() {
    try {
      const { data } = await api.getFlowTree(documentId)
      if (data.ready) setFlow(data)
    } catch (e) { /* 아직 없음 */ }
  }

  function handleExtractFlow() {
    setFlowBusy(true)
    setFlowMsg('흐름 트리 추출 중... (1~2분 소요)')
    api.startFlowTree(documentId).then(() => {
      let tries = 0
      flowPollRef.current = setInterval(async () => {
        tries += 1
        try {
          const { data } = await api.getFlowTree(documentId)
          if (data.ready) {
            clearInterval(flowPollRef.current)
            setFlow(data); setFlowBusy(false); setFlowMsg('')
          } else if (tries > 45) {   // ~3분 초과
            clearInterval(flowPollRef.current)
            setFlowBusy(false); setFlowMsg('추출이 지연되거나 실패했습니다. 잠시 후 다시 시도하세요.')
          }
        } catch (e) { /* 무시하고 계속 폴링 */ }
      }, 4000)
    }).catch(e => {
      setFlowBusy(false)
      setFlowMsg('추출 시작 실패: ' + (e.response?.data?.detail || e.message))
    })
  }

  async function handleGenerateTcFromFlow() {
    if (!window.confirm('흐름 트리를 기반으로 TC를 새로 생성합니다.\n이 문서의 기존 TC는 모두 교체(삭제 후 재생성)됩니다. 계속할까요?')) return
    setFlowBusy(true)
    setFlowMsg('흐름 트리에서 TC 생성 중...')
    try {
      await api.generateTcFromFlow(documentId)
      navigate(`/review/${documentId}`)
    } catch (e) {
      setFlowBusy(false)
      setFlowMsg('TC 생성 실패: ' + (e.response?.data?.detail || e.message))
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
        <div className="page-header">
          <h1>{tree?.title || '메뉴트리'}</h1>
          <p>기획서에서 추출한 트리를 검토하고 TC를 생성하세요. <strong>흐름 트리</strong>가 마스터이며, TC는 흐름 트리에서 파생됩니다.</p>
        </div>

        {/* 뷰 탭 */}
        <div style={{ display: 'flex', gap: 4, marginBottom: 16, borderBottom: '1px solid #e5e7eb' }}>
          {[['flow', '🌊 흐름 트리', '마스터'], ['structural', '🗂 구조적 트리', null]].map(([k, label, tag]) => (
            <button key={k} onClick={() => setView(k)}
              style={{
                padding: '10px 18px', border: 'none', background: 'none', cursor: 'pointer',
                fontSize: 14, fontWeight: view === k ? 700 : 500,
                color: view === k ? '#2563eb' : '#6b7280',
                borderBottom: view === k ? '2px solid #2563eb' : '2px solid transparent',
                marginBottom: -1,
              }}>
              {label}{tag && <span style={{ fontSize: 11, color: '#9ca3af', marginLeft: 4 }}>({tag})</span>}
            </button>
          ))}
        </div>

        {error && (
          <div style={{ padding: 12, background: '#fee2e2', borderRadius: 8, color: '#dc2626',
            marginBottom: 16, fontSize: 14 }}>
            {error}
          </div>
        )}

        {view === 'structural' && (
        <>
        <div className="card" style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ fontSize: 13, color: '#6b7280' }}>
            전체 기능 <strong>{totalFeatures}</strong>개 · 생성 대상 <strong style={{ color: '#16a34a' }}>{includeCount}</strong>개
            {excludedCount > 0 && <span style={{ color: '#ef4444' }}> · 제외 {excludedCount}개</span>}
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            {tree && (
              <a href={api.treeExportUrl(documentId)} target="_blank" rel="noreferrer"
                style={{ padding: '8px 14px', borderRadius: 8, border: '1px solid #d1d5db', background: '#fff',
                  color: '#374151', fontWeight: 600, fontSize: 14, textDecoration: 'none' }}>
                📥 메뉴트리 Excel
              </a>
            )}
            <button onClick={handleGenerateTc} disabled={generating || includeCount === 0}
              style={{ padding: '8px 18px', borderRadius: 8, border: 'none',
                background: generating ? '#9ca3af' : '#2563eb', color: '#fff', fontWeight: 700, fontSize: 14,
                cursor: generating ? 'not-allowed' : 'pointer' }}>
              {generating ? 'TC 생성중 ⟳' : '구조적 트리로 TC 생성 →'}
            </button>
          </div>
        </div>

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
        </>
        )}

        {/* 흐름 트리 (행동 흐름 메뉴트리) */}
        {view === 'flow' && (
        <div className="card" style={{ marginTop: 16 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <div>
              <h2 style={{ fontSize: 16, fontWeight: 700, margin: 0 }}>흐름 트리 <span style={{ fontSize: 12, color: '#6b7280', fontWeight: 400 }}>(행동 흐름 메뉴트리 · QA 양식)</span></h2>
              {flow?.stats && (
                <div style={{ fontSize: 12, color: '#6b7280', marginTop: 4 }}>
                  총 {flow.stats.total}노드 · 깊이 {flow.stats.max_depth} ·{' '}
                  {Object.entries(flow.stats.types).map(([t, n]) => `${t} ${n}`).join(' / ')}
                </div>
              )}
            </div>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexShrink: 0 }}>
              {!flow ? (
                <button onClick={handleExtractFlow} disabled={flowBusy}
                  style={{ padding: '8px 16px', borderRadius: 8, border: 'none', fontWeight: 600, fontSize: 14,
                    background: flowBusy ? '#9ca3af' : '#7c3aed', color: '#fff', cursor: flowBusy ? 'not-allowed' : 'pointer' }}>
                  {flowBusy ? '추출 중 ⟳' : '흐름 트리 추출'}
                </button>
              ) : (
                <>
                  <a href={api.flowTreeExportUrl(documentId)} target="_blank" rel="noreferrer"
                    style={{ padding: '8px 14px', borderRadius: 8, border: '1px solid #d1d5db', background: '#fff',
                      color: '#374151', fontWeight: 600, fontSize: 14, textDecoration: 'none' }}>
                    📥 Excel
                  </a>
                  <button onClick={handleExtractFlow} disabled={flowBusy}
                    style={{ padding: '8px 14px', borderRadius: 8, border: '1px solid #d1d5db', background: '#fff',
                      color: '#374151', fontWeight: 600, fontSize: 14, cursor: flowBusy ? 'not-allowed' : 'pointer' }}>
                    재추출
                  </button>
                  <button onClick={handleGenerateTcFromFlow} disabled={flowBusy}
                    style={{ padding: '8px 16px', borderRadius: 8, border: 'none', fontWeight: 700, fontSize: 14,
                      background: flowBusy ? '#9ca3af' : '#2563eb', color: '#fff', cursor: flowBusy ? 'not-allowed' : 'pointer' }}>
                    이 흐름트리로 TC 생성 →
                  </button>
                </>
              )}
            </div>
          </div>

          {flowMsg && (
            <div style={{ padding: 10, background: '#f5f3ff', borderRadius: 8, color: '#6d28d9', fontSize: 13, marginBottom: 12 }}>
              {flowBusy && <span className="spinner" style={{ width: 14, height: 14, borderTopColor: '#7c3aed', borderColor: '#ddd6fe', display: 'inline-block', marginRight: 8, verticalAlign: 'middle' }} />}
              {flowMsg}
            </div>
          )}

          {flow?.flow_tree?.tree ? (
            <div style={{ maxHeight: 600, overflowY: 'auto', padding: 4 }}>
              {flow.flow_tree.tree.map((node, i) => <FlowNode key={node.id || i} node={node} depth={0} />)}
            </div>
          ) : !flowBusy ? (
            <p style={{ fontSize: 13, color: '#9ca3af', margin: 0 }}>
              아직 흐름 트리가 없습니다. "흐름 트리 추출"을 누르면 상태→액션→표시결과 흐름으로 추출됩니다 (사람 QA 양식).
            </p>
          ) : null}
        </div>
        )}
      </div>
    </div>
  )
}
