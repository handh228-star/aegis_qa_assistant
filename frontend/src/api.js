import axios from 'axios'

const BASE = 'http://localhost:8000/api'

export const api = {
  // Projects
  getProjects: () => axios.get(`${BASE}/projects/`),
  createProject: (data) => axios.post(`${BASE}/projects/`, data),
  getProject: (id) => axios.get(`${BASE}/projects/${id}`),

  // Documents
  getDocuments: (projectId) => axios.get(`${BASE}/documents/${projectId}/`),
  uploadDocument: (projectId, file) => {
    const form = new FormData()
    form.append('file', file)
    return axios.post(`${BASE}/documents/${projectId}/upload`, form)
  },
  getDocumentStatus: (docId) => axios.get(`${BASE}/documents/status/${docId}`),

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
