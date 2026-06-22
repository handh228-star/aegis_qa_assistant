import axios from 'axios'

const BASE = `http://${window.location.hostname}:8000/api`

export const api = {
  // Projects
  getProjects: () => axios.get(`${BASE}/projects/`),
  createProject: (data) => axios.post(`${BASE}/projects/`, data),
  getProject: (id) => axios.get(`${BASE}/projects/${id}`),

  // Documents
  getDocuments: (projectId) => axios.get(`${BASE}/documents/${projectId}/`),
  uploadDocument: (projectId, file, tcLevel = 2) => {
    const form = new FormData()
    form.append('file', file)
    form.append('tc_level', tcLevel)
    return axios.post(`${BASE}/documents/${projectId}/upload`, form)
  },
  getDocumentStatus: (docId) => axios.get(`${BASE}/documents/status/${docId}`),
  getTree: (docId) => axios.get(`${BASE}/documents/${docId}/tree`),
  updateTree: (docId, tree) => axios.put(`${BASE}/documents/${docId}/tree`, tree),
  generateTc: (docId) => axios.post(`${BASE}/documents/${docId}/generate-tc`),
  treeExportUrl: (docId) => `${BASE}/documents/${docId}/tree/export`,

  // Flow Tree (흐름 트리 — 행동 흐름 메뉴트리)
  startFlowTree: (docId) => axios.post(`${BASE}/documents/${docId}/flow-tree`),
  getFlowTree: (docId) => axios.get(`${BASE}/documents/${docId}/flow-tree`),
  flowTreeExportUrl: (docId) => `${BASE}/documents/${docId}/flow-tree/export`,
  generateTcFromFlow: (docId) => axios.post(`${BASE}/documents/${docId}/flow-tree/generate-tc`),
  flowCoverageCheck: (docId) => axios.post(`${BASE}/documents/${docId}/flow-tree/coverage-check`),

  // RuleSets
  getRulesets: () => axios.get(`${BASE}/rulesets/`),
  getRuleset: (id) => axios.get(`${BASE}/rulesets/${id}`),
  createRuleset: (data) => axios.post(`${BASE}/rulesets/`, data),
  updateRuleset: (id, data) => axios.put(`${BASE}/rulesets/${id}`, data),
  deleteRuleset: (id) => axios.delete(`${BASE}/rulesets/${id}`),

  // TestCases
  getTestcases: (docId, filters = {}) =>
    axios.get(`${BASE}/testcases/document/${docId}`, { params: filters }),
  getSummary: (docId) => axios.get(`${BASE}/testcases/document/${docId}/summary`),
  reviewTc: (tcId, reviewStatus, reviewNote) =>
    axios.patch(`${BASE}/testcases/${tcId}/review`, {
      review_status: reviewStatus,
      review_note: reviewNote || null,
    }),
  deleteTc: (tcId) => axios.delete(`${BASE}/testcases/${tcId}`),
  regenerate: (docId) => axios.post(`${BASE}/testcases/document/${docId}/regenerate`),
  exportUrl: (docId) => `${BASE}/testcases/document/${docId}/export`,
}
