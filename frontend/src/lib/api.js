import axios from 'axios'
import { supabase } from './supabase'

const API_URL = import.meta.env.VITE_API_URL
const api = axios.create({ baseURL: API_URL })

api.interceptors.request.use(async (config) => {
  const { data: { session } } = await supabase.auth.getSession()
  if (session?.access_token) {
    config.headers.Authorization = "Bearer "+ session.access_token
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
