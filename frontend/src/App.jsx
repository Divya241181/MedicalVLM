import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Navbar         from './components/Navbar'
import ProtectedRoute from './components/ProtectedRoute'
import Login          from './pages/Login'
import Signup         from './pages/Signup'
import Analyze        from './pages/Analyze'
import Results        from './pages/Results'
import History        from './pages/History'
import Compare        from './pages/Compare'

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
        <Navbar />
        <Routes>
          <Route path="/login"   element={<Login />}  />
          <Route path="/signup"  element={<Signup />} />
          <Route path="/analyze" element={<ProtectedRoute><Analyze /></ProtectedRoute>} />
          <Route path="/results" element={<ProtectedRoute><Results /></ProtectedRoute>} />
          <Route path="/history" element={<ProtectedRoute><History /></ProtectedRoute>} />
          <Route path="/compare" element={<ProtectedRoute><Compare /></ProtectedRoute>} />
          <Route path="*"        element={<Navigate to="/login" replace />} />
        </Routes>
      </div>
    </BrowserRouter>
  )
}
