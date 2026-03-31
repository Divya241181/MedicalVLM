import { useState, useCallback } from 'react'
import { useNavigate }           from 'react-router-dom'
import { useDropzone }           from 'react-dropzone'
import { compareXrays }          from '../lib/api'

function XRayDropzone({ label, file, preview, onDrop, onClear }) {
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop: (acc, rej) => onDrop(acc, rej),
    accept: { 'image/jpeg': [], 'image/png': [] },
    maxSize: 20 * 1024 * 1024,
    multiple: false,
  })

  return (
    <div>
      <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">{label}</p>
      {!preview ? (
        <div
          {...getRootProps()}
          className={
            'border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ' +
            (isDragActive
              ? 'border-teal-500 bg-teal-50 dark:bg-teal-950'
              : 'border-gray-200 dark:border-gray-700 hover:border-teal-400')
          }
        >
          <input {...getInputProps()} />
          <p className="text-xs text-gray-500">{isDragActive ? 'Drop here' : 'Drag & drop or click to browse'}</p>
        </div>
      ) : (
        <div className="border border-gray-200 dark:border-gray-700 rounded-xl overflow-hidden">
          <img src={preview} alt={label} className="w-full object-contain max-h-52 bg-black" />
          <div className="flex items-center justify-between px-3 py-2 bg-white dark:bg-gray-900">
            <span className="text-xs text-gray-600 dark:text-gray-400 truncate">{file?.name}</span>
            <button onClick={onClear} className="text-xs text-gray-400 hover:text-red-500 ml-2">Remove</button>
          </div>
        </div>
      )}
    </div>
  )
}

export default function Compare() {
  const navigate = useNavigate()

  const [prevFile,    setPrevFile]    = useState(null)
  const [prevPreview, setPrevPreview] = useState(null)
  const [currFile,    setCurrFile]    = useState(null)
  const [currPreview, setCurrPreview] = useState(null)
  const [loading,     setLoading]     = useState(false)
  const [error,       setError]       = useState('')
  const [result,      setResult]      = useState(null)

  const handleDrop = (setFile, setPreview) => (accepted, rejected) => {
    if (rejected.length > 0) { setError('Only JPEG/PNG accepted (max 20 MB)'); return }
    setError('')
    setFile(accepted[0])
    setPreview(URL.createObjectURL(accepted[0]))
  }

  const handleCompare = async () => {
    if (!prevFile || !currFile) return
    setError('')
    setLoading(true)
    setResult(null)
    try {
      const data = await compareXrays(prevFile, currFile)
      setResult(data)
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Comparison failed.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-10">
      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">Compare X-Rays</h1>
        <p className="text-sm text-gray-500 mt-1">
          Upload two X-rays from different dates to get an interval change analysis
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        <XRayDropzone
          label="Previous X-Ray"
          file={prevFile} preview={prevPreview}
          onDrop={handleDrop(setPrevFile, setPrevPreview)}
          onClear={() => { setPrevFile(null); setPrevPreview(null) }}
        />
        <XRayDropzone
          label="Current X-Ray"
          file={currFile} preview={currPreview}
          onDrop={handleDrop(setCurrFile, setCurrPreview)}
          onClear={() => { setCurrFile(null); setCurrPreview(null) }}
        />
      </div>

      {error && (
        <div className="mb-4 text-sm text-red-600 bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded-lg px-4 py-3">
          {error}
        </div>
      )}

      <button
        id="compare-btn"
        onClick={handleCompare}
        disabled={!prevFile || !currFile || loading}
        className="w-full py-3 rounded-xl bg-teal-600 hover:bg-teal-700 text-white font-medium text-sm transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
      >
        {loading ? 'Comparing… (this may take several minutes)' : 'Compare X-Rays'}
      </button>

      <p className="text-xs text-gray-400 text-center mt-2">
        ⏱ First analysis may take 1–5 minutes while the model processes your image.
      </p>

      {result && (
        <div className="mt-8 space-y-6">
          <div className="border border-gray-200 dark:border-gray-700 rounded-2xl p-5 bg-white dark:bg-gray-900">
            <h2 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">🔄 Interval Changes</h2>
            <pre className="text-sm text-gray-800 dark:text-gray-200 leading-relaxed whitespace-pre-wrap font-sans">
              {result.interval_changes}
            </pre>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="border border-gray-200 dark:border-gray-700 rounded-2xl p-4 bg-white dark:bg-gray-900">
              <h3 className="text-xs font-medium uppercase tracking-wide text-gray-400 mb-2">Previous Report</h3>
              <pre className="text-xs text-gray-700 dark:text-gray-300 leading-relaxed whitespace-pre-wrap font-sans max-h-60 overflow-auto">
                {result.previous_report}
              </pre>
            </div>
            <div className="border border-gray-200 dark:border-gray-700 rounded-2xl p-4 bg-white dark:bg-gray-900">
              <h3 className="text-xs font-medium uppercase tracking-wide text-gray-400 mb-2">Current Report</h3>
              <pre className="text-xs text-gray-700 dark:text-gray-300 leading-relaxed whitespace-pre-wrap font-sans max-h-60 overflow-auto">
                {result.current_report}
              </pre>
            </div>
          </div>
          <p className="text-xs text-center text-gray-400">
            Processing time: {result.processing_time_ms?.toLocaleString()} ms
          </p>
        </div>
      )}

      <div className="mt-6 flex justify-center">
        <button onClick={() => navigate('/analyze')} className="text-sm text-teal-600 hover:text-teal-700 font-medium">
          ← Back to single analysis
        </button>
      </div>
    </div>
  )
}
