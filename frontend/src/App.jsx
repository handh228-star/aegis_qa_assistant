import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import ProjectsPage from './pages/ProjectsPage'
import DocumentsPage from './pages/DocumentsPage'
import TCReviewPage from './pages/TCReviewPage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<ProjectsPage />} />
        <Route path="/projects/:projectId" element={<DocumentsPage />} />
        <Route path="/review/:documentId" element={<TCReviewPage />} />
        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </BrowserRouter>
  )
}
