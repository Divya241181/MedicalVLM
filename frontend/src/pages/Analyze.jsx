import { useState, useCallback } from 'react'
import { useNavigate }           from 'react-router-dom'
import { useDropzone }           from 'react-dropzone'
import { generateReport, getBriefing } from '../lib/api'

export default function Analyze() {
  const navigate = useNavigate()

  const [file,           setFile]           = useState(null)
  const [preview,        setPreview]        = useState(null)
  const [loading,        setLoading]        = useState(false)
  const [error,          setError]          = useState('')
  const [step,           setStep]           = useState('')
  const [patientHistory, setPatientHistory] = useState('')

  const onDrop = useCallback((accepted, rejected) => {
    setError('')
    if (rejected.length > 0) {
      setError('Only JPEG and PNG files accepted (max 20 MB)')
      return
    }
    const f = accepted[0]
    setFile(f)
    setPreview(URL.createObjectURL(f))
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'image/jpeg': [], 'image/png': [] },
    maxSize: 20 * 1024 * 1024,
    multiple: false,
  })

  const handleGenerate = async () => {
    if (!file) return
    setError('')
    setLoading(true)
    try {
      setStep('Uploading image…')
      await new Promise(r => setTimeout(r, 500))
      setStep('Running LLaVA inference…')
      const [result, briefingResult] = await Promise.all([
        generateReport(file, patientHistory),
        getBriefing(file),
      ])
      setStep('Building GradCAM heatmap…')
      await new Promise(r => setTimeout(r, 300))

      sessionStorage.setItem('vlm_result',   JSON.stringify({ ...result, briefing: briefingResult.briefing }))
      sessionStorage.setItem('vlm_preview',  preview)
      sessionStorage.setItem('vlm_file_name', file.name)
      sessionStorage.setItem('vlm_history',  patientHistory)
      navigate('/results')
    } catch (err) {
      setError(
        err.response?.data?.detail ||
        err.message ||
        'Failed to generate report. Please try again.'
      )
    } finally {
      setLoading(false)
      setStep('')
    }
  }

  const handleClear = () => {
    setFile(null)
    setPreview(null)
    setError('')
    setPatientHistory('')
  }

  return (
    <div className="max-w-2xl mx-auto px-4 py-10">
      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">Analyze X-Ray</h1>
        <p className="text-sm text-gray-500 mt-1">
          Upload a chest X-ray to generate an AI-powered structured radiology report
        </p>
      </div>

      {/* ── Patient history ── */}
      <div className="mb-5">
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
          Patient History <span className="text-gray-400 font-normal">(optional)</span>
        </label>
        <textarea
          id="patient-history"
          rows={3}
          value={patientHistory}
          onChange={e => setPatientHistory(e.target.value)}
          placeholder="e.g. 65-year-old male with 3-week productive cough and low-grade fever…"
          className="w-full rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900
                     text-sm text-gray-800 dark:text-gray-200 placeholder-gray-400
                     px-4 py-3 resize-none focus:outline-none focus:ring-2 focus:ring-teal-500 transition"
        />
      </div>

      {/* ── Drop zone / preview ── */}
      {!preview ? (
        <div
          {...getRootProps()}
          className={
            'border-2 border-dashed rounded-2xl p-12 text-center cursor-pointer transition-colors ' +
            (isDragActive
              ? 'border-teal-500 bg-teal-50 dark:bg-teal-950'
              : 'border-gray-200 dark:border-gray-700 hover:border-teal-400')
          }
        >
          <input {...getInputProps()} />
          <div className="w-12 h-12 rounded-xl bg-gray-100 dark:bg-gray-800 flex items-center justify-center mx-auto mb-4">
            <svg className="w-6 h-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
            </svg>
          </div>
          <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
            {isDragActive ? 'Drop your X-ray here' : 'Drag and drop your X-ray'}
          </p>
          <p className="text-xs text-gray-400 mt-1">or click to browse — JPEG or PNG, max 20 MB</p>
        </div>
      ) : (
        <div className="border border-gray-200 dark:border-gray-700 rounded-2xl overflow-hidden">
          <img src={preview} alt="X-ray preview" className="w-full object-contain max-h-80 bg-black" />
          <div className="p-4 flex items-center justify-between bg-white dark:bg-gray-900">
            <div>
              <p className="text-sm font-medium text-gray-900 dark:text-white">{file.name}</p>
              <p className="text-xs text-gray-400 mt-0.5">{(file.size / 1024).toFixed(0)} KB</p>
            </div>
            <button onClick={handleClear} className="text-xs text-gray-500 hover:text-red-500 transition-colors">
              Remove
            </button>
          </div>
        </div>
      )}

      {error && (
        <div className="mt-4 text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded-lg px-4 py-3">
          {error}
        </div>
      )}
      {loading && (
        <div className="mt-4 bg-teal-50 dark:bg-teal-950 border border-teal-200 dark:border-teal-800 rounded-lg px-4 py-3">
          <div className="flex items-center gap-3">
            <svg className="animate-spin w-4 h-4 text-teal-600" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
            </svg>
            <span className="text-sm text-teal-700 dark:text-teal-300">{step}</span>
          </div>
        </div>
      )}

      <button
        id="generate-btn"
        onClick={handleGenerate}
        disabled={!file || loading}
        className="mt-6 w-full py-3 rounded-xl bg-teal-600 hover:bg-teal-700 text-white font-medium text-sm transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
      >
        {loading ? 'Generating…' : 'Generate Report'}
      </button>

      <p className="text-xs text-gray-400 text-center mt-2">
        ⏱ First analysis may take 1–5 minutes while the model processes your image.
      </p>

      {!preview && (
        <p className="text-center text-xs text-gray-400 mt-4">
          No X-ray? Use any chest X-ray PNG from your Kaggle test outputs
        </p>
      )}
    </div>
  )
}
