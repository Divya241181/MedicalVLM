/**
 * api.js — MedicalVLM API layer
 * All calls automatically inject the Supabase Bearer token.
 */
import axios from 'axios'
import { supabase } from './supabase'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({ baseURL: API_URL })

// ── Attach auth token to every request ───────────────────────────────
api.interceptors.request.use(async (config) => {
  const { data: { session } } = await supabase.auth.getSession()
  if (session?.access_token) {
    config.headers.Authorization = `Bearer ${session.access_token}`
  }
  return config
})

// ── /generate ────────────────────────────────────────────────────────
/**
 * Generate a full structured radiology report.
 * @param {File}   imageFile
 * @param {string} patientHistory  Optional free-text patient history
 */
export const generateReport = async (imageFile, patientHistory = '') => {
  const formData = new FormData()
  formData.append('file', imageFile)
  formData.append('patient_history', patientHistory)
  const res = await api.post('/generate', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 300_000,   // allow up to 5 min for large models
  })
  return res.data
}

// ── /briefing ────────────────────────────────────────────────────────
/**
 * Get a plain-English, patient-friendly summary (3-5 sentences).
 * @param {File} imageFile
 */
export const getBriefing = async (imageFile) => {
  const formData = new FormData()
  formData.append('file', imageFile)
  const res = await api.post('/briefing', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 180_000,
  })
  return res.data
}

// ── /compare ─────────────────────────────────────────────────────────
/**
 * Compare two X-rays for interval changes.
 * @param {File} prevFile   Older X-ray
 * @param {File} currFile   Current X-ray
 */
export const compareXrays = async (prevFile, currFile) => {
  const formData = new FormData()
  formData.append('file_prev', prevFile)
  formData.append('file_curr', currFile)
  const res = await api.post('/compare', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 600_000,   // two inferences → 10 min
  })
  return res.data
}

// ── /export-pdf ──────────────────────────────────────────────────────
/**
 * Export a PDF report and trigger browser download.
 * @param {File}   imageFile
 * @param {string} patientHistory
 * @param {string} report          Optional: provide existing report text to skip inference
 * @param {string} filename        Suggested download filename
 */
export const exportPDF = async (imageFile, patientHistory = '', report = '', filename = 'medvlm_report.pdf') => {
  const formData = new FormData()
  formData.append('file', imageFile)
  formData.append('patient_history', patientHistory)
  formData.append('report', report)

  const res = await api.post('/export-pdf', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    responseType: 'blob',
    timeout: 300_000,
  })

  // Trigger browser download
  const url  = window.URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }))
  const link = document.createElement('a')
  link.href  = url
  link.setAttribute('download', filename)
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(url)
}

// ── /history ─────────────────────────────────────────────────────────
export const getHistory = async (limit = 20, offset = 0) => {
  const res = await api.get('/history', { params: { limit, offset } })
  return res.data
}

// ── /health ──────────────────────────────────────────────────────────
export const checkHealth = async () => {
  const res = await api.get('/health')
  return res.data
}
