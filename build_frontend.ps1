# ── Create frontend with Vite ─────────────────────────────────────
npm create vite@latest frontend --yes -- --template react
cd frontend
npm install
npm install @supabase/supabase-js axios react-router-dom react-dropzone recharts lucide-react
npm install @radix-ui/react-slot class-variance-authority clsx tailwind-merge
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p

# ── tailwind.config.js ───────────────────────────────────────────
@"
/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        teal: {
          50:  '#d1f2eb',
          100: '#a3e4d7',
          400: '#1abc9c',
          600: '#1D9E75',
          700: '#0F6E56',
          800: '#085041',
        }
      }
    },
  },
  plugins: [],
}
"@ | Set-Content tailwind.config.js

# ── src/index.css ─────────────────────────────────────────────────
@"
@tailwind base;
@tailwind components;
@tailwind utilities;
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  -webkit-font-smoothing: antialiased;
}
"@ | Set-Content src\index.css

# ── .env ──────────────────────────────────────────────────────────
@"
VITE_SUPABASE_URL=your-supabase-url
VITE_SUPABASE_ANON_KEY=your-supabase-anon-key
VITE_API_URL=http://localhost:8001
"@ | Set-Content .env

# ── Create folders ────────────────────────────────────────────────
New-Item -ItemType Directory -Force -Path src\components
New-Item -ItemType Directory -Force -Path src\pages
New-Item -ItemType Directory -Force -Path src\lib
New-Item -ItemType Directory -Force -Path src\hooks

# ── src/lib/supabase.js ───────────────────────────────────────────
@"
import { createClient } from '@supabase/supabase-js'
const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseKey = import.meta.env.VITE_SUPABASE_ANON_KEY
export const supabase = createClient(supabaseUrl, supabaseKey)
"@ | Set-Content src\lib\supabase.js

# ── src/lib/api.js ────────────────────────────────────────────────
@"
import axios from 'axios'
import { supabase } from './supabase'

const API_URL = import.meta.env.VITE_API_URL
const api = axios.create({ baseURL: API_URL })

api.interceptors.request.use(async (config) => {
  const { data: { session } } = await supabase.auth.getSession()
  if (session?.access_token) {
    config.headers.Authorization = `"Bearer "`+ session.access_token
  }
  return config
})

export const generateReport = async (imageFile) => {
  const formData = new FormData()
  formData.append('file', imageFile)
  const res = await api.post('/generate', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
  return res.data
}

export const getHistory = async () => {
  const res = await api.get('/history')
  return res.data
}

export const checkHealth = async () => {
  const res = await api.get('/health')
  return res.data
}
"@ | Set-Content src\lib\api.js

# ── src/hooks/useAuth.js ──────────────────────────────────────────
@"
import { useEffect, useState } from 'react'
import { supabase } from '../lib/supabase'

export function useAuth() {
  const [user,    setUser]    = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setUser(session?.user ?? null)
      setLoading(false)
    })
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (_event, session) => { setUser(session?.user ?? null) }
    )
    return () => subscription.unsubscribe()
  }, [])

  const signOut = async () => {
    await supabase.auth.signOut()
    setUser(null)
  }

  return { user, loading, signOut }
}
"@ | Set-Content src\hooks\useAuth.js

# ── src/components/ProtectedRoute.jsx ────────────────────────────
@"
import { Navigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

export default function ProtectedRoute({ children }) {
  const { user, loading } = useAuth()
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-gray-500 text-sm">Loading...</div>
      </div>
    )
  }
  if (!user) return <Navigate to="/login" replace />
  return children
}
"@ | Set-Content src\components\ProtectedRoute.jsx

# ── src/components/Navbar.jsx ─────────────────────────────────────
@"
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { useState } from 'react'

export default function Navbar() {
  const { user, signOut } = useAuth()
  const navigate          = useNavigate()
  const [dark, setDark]   = useState(false)

  const toggleDark = () => {
    setDark(!dark)
    document.documentElement.classList.toggle('dark')
  }

  const handleSignOut = async () => {
    await signOut()
    navigate('/login')
  }

  return (
    <nav className="border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-6 py-3 flex items-center justify-between sticky top-0 z-50">
      <Link to="/analyze" className="flex items-center gap-2 font-semibold text-gray-900 dark:text-white text-sm">
        <div className="w-7 h-7 rounded-lg bg-teal-600 flex items-center justify-center text-white text-xs font-bold">M</div>
        MedVLM
      </Link>
      {user && (
        <div className="flex items-center gap-6 text-sm">
          <Link to="/analyze" className="text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white transition-colors">Analyze</Link>
          <Link to="/history" className="text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white transition-colors">History</Link>
        </div>
      )}
      <div className="flex items-center gap-3">
        <button onClick={toggleDark} className="text-xs px-3 py-1.5 rounded-lg border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
          {dark ? 'Light' : 'Dark'}
        </button>
        {user && (
          <>
            <span className="text-xs text-gray-400 hidden sm:block">{user?.email}</span>
            <button onClick={handleSignOut} className="text-xs px-3 py-1.5 rounded-lg bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors">Sign out</button>
          </>
        )}
      </div>
    </nav>
  )
}
"@ | Set-Content src\components\Navbar.jsx

# ── src/pages/Login.jsx ───────────────────────────────────────────
@"
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { supabase } from '../lib/supabase'

export default function Login() {
  const navigate = useNavigate()
  const [email,    setEmail]    = useState('')
  const [password, setPassword] = useState('')
  const [error,    setError]    = useState('')
  const [loading,  setLoading]  = useState(false)

  const handleLogin = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    const { error } = await supabase.auth.signInWithPassword({ email, password })
    if (error) { setError(error.message) } else { navigate('/analyze') }
    setLoading(false)
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 flex items-center justify-center px-4">
      <div className="w-full max-w-sm bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-2xl p-8">
        <div className="text-center mb-8">
          <div className="w-12 h-12 rounded-xl bg-teal-600 flex items-center justify-center text-white text-xl font-bold mx-auto mb-3">M</div>
          <h1 className="text-xl font-semibold text-gray-900 dark:text-white">Sign in to MedVLM</h1>
          <p className="text-sm text-gray-500 mt-1">AI-powered chest X-ray report generation</p>
        </div>
        <form onSubmit={handleLogin} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Email</label>
            <input type="email" value={email} onChange={e => setEmail(e.target.value)} required placeholder="you@example.com"
              className="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 placeholder-gray-400" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Password</label>
            <input type="password" value={password} onChange={e => setPassword(e.target.value)} required placeholder="••••••••"
              className="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 placeholder-gray-400" />
          </div>
          {error && <div className="text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded-lg px-3 py-2">{error}</div>}
          <button type="submit" disabled={loading}
            className="w-full py-2.5 rounded-lg bg-teal-600 hover:bg-teal-700 text-white text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed">
            {loading ? 'Signing in...' : 'Sign in'}
          </button>
        </form>
        <p className="text-center text-sm text-gray-500 mt-6">
          No account? <Link to="/signup" className="text-teal-600 hover:text-teal-700 font-medium">Sign up free</Link>
        </p>
      </div>
    </div>
  )
}
"@ | Set-Content src\pages\Login.jsx

# ── src/pages/Signup.jsx ──────────────────────────────────────────
@"
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { supabase } from '../lib/supabase'

export default function Signup() {
  const navigate = useNavigate()
  const [email,    setEmail]    = useState('')
  const [password, setPassword] = useState('')
  const [confirm,  setConfirm]  = useState('')
  const [error,    setError]    = useState('')
  const [loading,  setLoading]  = useState(false)

  const handleSignup = async (e) => {
    e.preventDefault()
    setError('')
    if (password !== confirm) { setError('Passwords do not match'); return }
    if (password.length < 6)  { setError('Password must be at least 6 characters'); return }
    setLoading(true)
    const { error } = await supabase.auth.signUp({ email, password })
    if (error) { setError(error.message) } else { navigate('/analyze') }
    setLoading(false)
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 flex items-center justify-center px-4">
      <div className="w-full max-w-sm bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-2xl p-8">
        <div className="text-center mb-8">
          <div className="w-12 h-12 rounded-xl bg-teal-600 flex items-center justify-center text-white text-xl font-bold mx-auto mb-3">M</div>
          <h1 className="text-xl font-semibold text-gray-900 dark:text-white">Create your account</h1>
          <p className="text-sm text-gray-500 mt-1">Free — no credit card required</p>
        </div>
        <form onSubmit={handleSignup} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Email</label>
            <input type="email" value={email} onChange={e => setEmail(e.target.value)} required placeholder="you@example.com"
              className="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 placeholder-gray-400" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Password</label>
            <input type="password" value={password} onChange={e => setPassword(e.target.value)} required placeholder="min 6 characters"
              className="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 placeholder-gray-400" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Confirm password</label>
            <input type="password" value={confirm} onChange={e => setConfirm(e.target.value)} required placeholder="••••••••"
              className="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 placeholder-gray-400" />
          </div>
          {error && <div className="text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded-lg px-3 py-2">{error}</div>}
          <button type="submit" disabled={loading}
            className="w-full py-2.5 rounded-lg bg-teal-600 hover:bg-teal-700 text-white text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed">
            {loading ? 'Creating account...' : 'Create account'}
          </button>
        </form>
        <p className="text-center text-sm text-gray-500 mt-6">
          Already have an account? <Link to="/login" className="text-teal-600 hover:text-teal-700 font-medium">Sign in</Link>
        </p>
      </div>
    </div>
  )
}
"@ | Set-Content src\pages\Signup.jsx

# ── src/pages/Analyze.jsx ─────────────────────────────────────────
@"
import { useState, useCallback } from 'react'
import { useNavigate }           from 'react-router-dom'
import { useDropzone }           from 'react-dropzone'
import { generateReport }        from '../lib/api'

export default function Analyze() {
  const navigate              = useNavigate()
  const [file,    setFile]    = useState(null)
  const [preview, setPreview] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState('')
  const [step,    setStep]    = useState('')

  const onDrop = useCallback((accepted, rejected) => {
    setError('')
    if (rejected.length > 0) { setError('Only JPEG and PNG files accepted (max 10MB)'); return }
    const f = accepted[0]
    setFile(f)
    setPreview(URL.createObjectURL(f))
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop, accept: { 'image/jpeg': [], 'image/png': [] },
    maxSize: 10 * 1024 * 1024, multiple: false
  })

  const handleGenerate = async () => {
    if (!file) return
    setError(''); setLoading(true)
    try {
      setStep('Encoding image...')
      await new Promise(r => setTimeout(r, 800))
      setStep('Generating report tokens...')
      const result = await generateReport(file)
      setStep('Building attention map...')
      await new Promise(r => setTimeout(r, 400))
      sessionStorage.setItem('vlm_result',  JSON.stringify(result))
      sessionStorage.setItem('vlm_preview', preview)
      navigate('/results')
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to generate report. Please try again.')
    } finally { setLoading(false); setStep('') }
  }

  const handleClear = () => { setFile(null); setPreview(null); setError('') }

  return (
    <div className="max-w-2xl mx-auto px-4 py-10">
      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">Analyze X-Ray</h1>
        <p className="text-sm text-gray-500 mt-1">Upload a chest X-ray image to generate an AI diagnostic report</p>
      </div>
      {!preview ? (
        <div {...getRootProps()} className={"border-2 border-dashed rounded-2xl p-12 text-center cursor-pointer transition-colors " + (isDragActive ? "border-teal-500 bg-teal-50 dark:bg-teal-950" : "border-gray-200 dark:border-gray-700 hover:border-teal-400")}>
          <input {...getInputProps()} />
          <div className="w-12 h-12 rounded-xl bg-gray-100 dark:bg-gray-800 flex items-center justify-center mx-auto mb-4">
            <svg className="w-6 h-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"/>
            </svg>
          </div>
          <p className="text-sm font-medium text-gray-700 dark:text-gray-300">{isDragActive ? 'Drop your X-ray here' : 'Drag and drop your X-ray'}</p>
          <p className="text-xs text-gray-400 mt-1">or click to browse — JPEG or PNG, max 10MB</p>
        </div>
      ) : (
        <div className="border border-gray-200 dark:border-gray-700 rounded-2xl overflow-hidden">
          <img src={preview} alt="X-ray preview" className="w-full object-contain max-h-80 bg-black" />
          <div className="p-4 flex items-center justify-between bg-white dark:bg-gray-900">
            <div>
              <p className="text-sm font-medium text-gray-900 dark:text-white">{file.name}</p>
              <p className="text-xs text-gray-400 mt-0.5">{(file.size / 1024).toFixed(0)} KB</p>
            </div>
            <button onClick={handleClear} className="text-xs text-gray-500 hover:text-red-500 transition-colors">Remove</button>
          </div>
        </div>
      )}
      {error && <div className="mt-4 text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded-lg px-4 py-3">{error}</div>}
      {loading && <div className="mt-4 bg-teal-50 dark:bg-teal-950 border border-teal-200 dark:border-teal-800 rounded-lg px-4 py-3 text-sm text-teal-700 dark:text-teal-300">{step}</div>}
      <button onClick={handleGenerate} disabled={!file || loading}
        className="mt-6 w-full py-3 rounded-xl bg-teal-600 hover:bg-teal-700 text-white font-medium text-sm transition-colors disabled:opacity-40 disabled:cursor-not-allowed">
        {loading ? 'Generating...' : 'Generate Report'}
      </button>
      {!preview && <p className="text-center text-xs text-gray-400 mt-4">No X-ray? Use any chest X-ray PNG from your Kaggle test outputs</p>}
    </div>
  )
}
"@ | Set-Content src\pages\Analyze.jsx

# ── src/pages/Results.jsx ─────────────────────────────────────────
@"
import { useEffect, useState } from 'react'
import { useNavigate }         from 'react-router-dom'

export default function Results() {
  const navigate             = useNavigate()
  const [result,   setResult]   = useState(null)
  const [preview,  setPreview]  = useState(null)
  const [opacity,  setOpacity]  = useState(60)
  const [showHeat, setShowHeat] = useState(true)
  const [copied,   setCopied]   = useState(false)

  useEffect(() => {
    const stored        = sessionStorage.getItem('vlm_result')
    const storedPreview = sessionStorage.getItem('vlm_preview')
    if (!stored) { navigate('/analyze'); return }
    setResult(JSON.parse(stored))
    setPreview(storedPreview)
  }, [navigate])

  if (!result) return null

  const handleCopy = () => {
    navigator.clipboard.writeText(result.report)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">Report Results</h1>
          <p className="text-sm text-gray-500 mt-0.5">AI-generated chest X-ray report</p>
        </div>
        <button onClick={() => navigate('/analyze')} className="text-sm px-4 py-2 rounded-lg border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">New analysis</button>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="border border-gray-200 dark:border-gray-700 rounded-2xl overflow-hidden bg-white dark:bg-gray-900">
          <div className="relative bg-black">
            <img src={preview} alt="X-ray" className="w-full object-contain max-h-72" />
            {result.attention_map && showHeat && (
              <img src={"data:image/png;base64," + result.attention_map} alt="Attention heatmap"
                className="absolute inset-0 w-full h-full object-contain" style={{ opacity: opacity / 100 }} />
            )}
          </div>
          <div className="p-4 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-gray-600 dark:text-gray-400">Attention heatmap</span>
              <button onClick={() => setShowHeat(!showHeat)}
                className={"text-xs px-3 py-1 rounded-full border transition-colors " + (showHeat ? "bg-teal-50 border-teal-200 text-teal-700 dark:bg-teal-950 dark:border-teal-800 dark:text-teal-300" : "border-gray-200 text-gray-500 dark:border-gray-700")}>
                {showHeat ? 'ON' : 'OFF'}
              </button>
            </div>
            {showHeat && (
              <div className="flex items-center gap-3">
                <span className="text-xs text-gray-400 w-14">Opacity</span>
                <input type="range" min="10" max="90" value={opacity}
                  onChange={e => setOpacity(Number(e.target.value))} className="flex-1 accent-teal-600" />
                <span className="text-xs text-gray-400 w-8 text-right">{opacity}%</span>
              </div>
            )}
          </div>
        </div>
        <div className="flex flex-col gap-4">
          <div className="border border-gray-200 dark:border-gray-700 rounded-2xl p-5 bg-white dark:bg-gray-900 flex-1">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-medium uppercase tracking-wide text-gray-400">Generated Report</span>
              <button onClick={handleCopy} className="text-xs px-3 py-1 rounded-lg bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors">
                {copied ? 'Copied!' : 'Copy'}
              </button>
            </div>
            <p className="text-sm text-gray-800 dark:text-gray-200 leading-relaxed">{result.report || 'No report generated.'}</p>
          </div>
          <div className="grid grid-cols-3 gap-3">
            {[
              { label: 'BLEU-4',  value: result.bleu4  ?? '-' },
              { label: 'ROUGE-L', value: result.rougeL ?? '-' },
              { label: 'Latency', value: result.latency_ms ? result.latency_ms + 'ms' : '-' },
            ].map(m => (
              <div key={m.label} className="bg-gray-50 dark:bg-gray-800 rounded-xl p-3 text-center">
                <div className="text-lg font-semibold text-gray-900 dark:text-white">
                  {typeof m.value === 'number' ? m.value.toFixed(2) : m.value}
                </div>
                <div className="text-xs text-gray-400 mt-0.5">{m.label}</div>
              </div>
            ))}
          </div>
          <div className="text-xs text-amber-700 dark:text-amber-400 bg-amber-50 dark:bg-amber-950 border border-amber-200 dark:border-amber-800 rounded-lg px-3 py-2">
            For research use only. Not for clinical diagnosis.
          </div>
          <div className="flex gap-3">
            <button onClick={() => navigate('/history')} className="flex-1 py-2 rounded-lg border border-gray-200 dark:border-gray-700 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">View history</button>
            <button onClick={() => navigate('/analyze')} className="flex-1 py-2 rounded-lg bg-teal-600 hover:bg-teal-700 text-white text-sm font-medium transition-colors">New analysis</button>
          </div>
        </div>
      </div>
    </div>
  )
}
"@ | Set-Content src\pages\Results.jsx

# ── src/pages/History.jsx ─────────────────────────────────────────
@"
import { useEffect, useState } from 'react'
import { useNavigate }         from 'react-router-dom'
import { getHistory }          from '../lib/api'

export default function History() {
  const navigate             = useNavigate()
  const [reports,  setReports]  = useState([])
  const [loading,  setLoading]  = useState(true)
  const [error,    setError]    = useState('')

  useEffect(() => {
    getHistory()
      .then(data => setReports(data.reports || []))
      .catch(()  => setError('Failed to load history'))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">Report History</h1>
        <p className="text-sm text-gray-500 mt-1">All your previously generated reports</p>
      </div>
      {loading && <div className="text-sm text-gray-400 text-center py-16">Loading...</div>}
      {error   && <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-4 py-3">{error}</div>}
      {!loading && !error && reports.length === 0 && (
        <div className="text-center py-16">
          <p className="text-gray-400 text-sm">No reports yet.</p>
          <button onClick={() => navigate('/analyze')} className="mt-4 text-sm text-teal-600 hover:text-teal-700 font-medium">Analyze your first X-ray</button>
        </div>
      )}
      {reports.length > 0 && (
        <div className="border border-gray-200 dark:border-gray-700 rounded-2xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 dark:bg-gray-800 text-left">
                <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Image</th>
                <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Report excerpt</th>
                <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">BLEU-4</th>
                <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Date</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
              {reports.map(r => (
                <tr key={r.id} className="bg-white dark:bg-gray-900 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
                  <td className="px-4 py-3 text-gray-700 dark:text-gray-300 font-mono text-xs">{r.image_name}</td>
                  <td className="px-4 py-3 text-gray-600 dark:text-gray-400 max-w-xs">{r.generated_report?.slice(0, 80)}{r.generated_report?.length > 80 ? '...' : ''}</td>
                  <td className="px-4 py-3 text-gray-700 dark:text-gray-300">{r.bleu_score != null ? r.bleu_score.toFixed(3) : '-'}</td>
                  <td className="px-4 py-3 text-gray-400 text-xs whitespace-nowrap">{new Date(r.created_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
"@ | Set-Content src\pages\History.jsx

# ── src/App.jsx ───────────────────────────────────────────────────
@"
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Navbar         from './components/Navbar'
import ProtectedRoute from './components/ProtectedRoute'
import Login          from './pages/Login'
import Signup         from './pages/Signup'
import Analyze        from './pages/Analyze'
import Results        from './pages/Results'
import History        from './pages/History'

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
          <Route path="*"        element={<Navigate to="/login" replace />} />
        </Routes>
      </div>
    </BrowserRouter>
  )
}
"@ | Set-Content src\App.jsx

Write-Host ""
Write-Host "All files created successfully." -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Open frontend\.env and fill in your Supabase URL and anon key"
Write-Host "  2. Run: npm run dev"
Write-Host "  3. Open http://localhost:5173"
