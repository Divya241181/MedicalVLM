import { useEffect, useState } from 'react'
import { useNavigate }         from 'react-router-dom'
import { exportPDF }           from '../lib/api'

export default function Results() {
  const navigate = useNavigate()

  const [result,         setResult]         = useState(null)
  const [preview,        setPreview]        = useState(null)
  const [opacity,        setOpacity]        = useState(60)
  const [showHeat,       setShowHeat]       = useState(true)
  const [copied,         setCopied]         = useState(false)
  const [activeTab,      setActiveTab]      = useState('report')   // 'report' | 'briefing'
  const [pdfLoading,     setPdfLoading]     = useState(false)
  const [pdfError,       setPdfError]       = useState('')

  useEffect(() => {
    const stored        = sessionStorage.getItem('vlm_result')
    const storedPreview = sessionStorage.getItem('vlm_preview')
    if (!stored) { navigate('/analyze'); return }
    setResult(JSON.parse(stored))
    setPreview(storedPreview)
  }, [navigate])

  if (!result) return null

  const heatmap = result.heatmap_base64 || result.attention_map
  const briefing = result.briefing

  const handleCopy = () => {
    navigator.clipboard.writeText(result.report)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handlePdfDownload = async () => {
    try {
      setPdfLoading(true)
      setPdfError('')
      const storedFileName = sessionStorage.getItem('vlm_file_name') || 'xray.png'
      const storedHistory  = sessionStorage.getItem('vlm_history')  || ''
      const storedPreview  = sessionStorage.getItem('vlm_preview')

      // Re-fetch the original file from data URL if needed
      // Since we stored the object URL, we need to re-upload the file
      // Instead pass enough context to the PDF endpoint
      // We'll use fetch + FormData with the original blob
      const blobRes  = await fetch(storedPreview)
      const blobData = await blobRes.blob()
      const fileObj  = new File([blobData], storedFileName, { type: blobData.type })

      await exportPDF(fileObj, storedHistory, result.report, `medvlm_report_${Date.now()}.pdf`)
    } catch (err) {
      setPdfError('PDF export failed — ' + (err.response?.data?.detail || err.message))
    } finally {
      setPdfLoading(false)
    }
  }

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      {/* ── Header ── */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">Report Results</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            AI-generated chest X-ray analysis
            {result.processing_time_ms && (
              <span className="ml-2 text-gray-400">· {result.processing_time_ms.toLocaleString()} ms</span>
            )}
          </p>
        </div>
        <div className="flex gap-2">
          <button
            id="pdf-download-btn"
            onClick={handlePdfDownload}
            disabled={pdfLoading}
            className="text-sm px-4 py-2 rounded-lg bg-teal-600 hover:bg-teal-700 text-white font-medium transition-colors disabled:opacity-50 flex items-center gap-2"
          >
            {pdfLoading ? (
              <>
                <svg className="animate-spin w-3.5 h-3.5" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
                </svg>
                Exporting…
              </>
            ) : (
              <>
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5 5-5M12 3v12"/>
                </svg>
                Download PDF
              </>
            )}
          </button>
          <button
            onClick={() => navigate('/analyze')}
            className="text-sm px-4 py-2 rounded-lg border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
          >
            New analysis
          </button>
        </div>
      </div>

      {pdfError && (
        <div className="mb-4 text-sm text-red-600 bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded-lg px-4 py-3">
          {pdfError}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* ── Left: image + heatmap ── */}
        <div className="border border-gray-200 dark:border-gray-700 rounded-2xl overflow-hidden bg-white dark:bg-gray-900">
          <div className="relative bg-black">
            <img src={preview} alt="X-ray" className="w-full object-contain max-h-72" />
            {heatmap && showHeat && (
              <img
                src={`data:image/png;base64,${heatmap}`}
                alt="GradCAM heatmap"
                className="absolute inset-0 w-full h-full object-contain"
                style={{ opacity: opacity / 100 }}
              />
            )}
          </div>
          <div className="p-4 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-gray-600 dark:text-gray-400">GradCAM heatmap</span>
              <button
                onClick={() => setShowHeat(!showHeat)}
                className={
                  'text-xs px-3 py-1 rounded-full border transition-colors ' +
                  (showHeat
                    ? 'bg-teal-50 border-teal-200 text-teal-700 dark:bg-teal-950 dark:border-teal-800 dark:text-teal-300'
                    : 'border-gray-200 text-gray-500 dark:border-gray-700')
                }
              >
                {showHeat ? 'ON' : 'OFF'}
              </button>
            </div>
            {showHeat && (
              <div className="flex items-center gap-3">
                <span className="text-xs text-gray-400 w-14">Opacity</span>
                <input
                  type="range" min="10" max="90" value={opacity}
                  onChange={e => setOpacity(Number(e.target.value))}
                  className="flex-1 accent-teal-600"
                />
                <span className="text-xs text-gray-400 w-8 text-right">{opacity}%</span>
              </div>
            )}
            {result.confidence_level && (
              <div className="flex items-center justify-between pt-1 border-t border-gray-100 dark:border-gray-800">
                <span className="text-xs text-gray-400">Model confidence</span>
                <span className={
                  'text-xs font-medium px-2 py-0.5 rounded-full ' +
                  (result.confidence_level === 'High'
                    ? 'bg-green-50 text-green-700 dark:bg-green-950 dark:text-green-300'
                    : 'bg-yellow-50 text-yellow-700 dark:bg-yellow-950 dark:text-yellow-300')
                }>
                  {result.confidence_level}
                </span>
              </div>
            )}
          </div>
        </div>

        {/* ── Right: tabs (report / briefing) + actions ── */}
        <div className="flex flex-col gap-4">
          {/* Tab selector */}
          <div className="flex rounded-xl overflow-hidden border border-gray-200 dark:border-gray-700">
            <button
              onClick={() => setActiveTab('report')}
              className={
                'flex-1 py-2.5 text-xs font-medium transition-colors ' +
                (activeTab === 'report'
                  ? 'bg-teal-600 text-white'
                  : 'bg-white dark:bg-gray-900 text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800')
              }
            >
              📋 Clinical Report
            </button>
            {briefing && (
              <button
                onClick={() => setActiveTab('briefing')}
                className={
                  'flex-1 py-2.5 text-xs font-medium transition-colors border-l border-gray-200 dark:border-gray-700 ' +
                  (activeTab === 'briefing'
                    ? 'bg-teal-600 text-white'
                    : 'bg-white dark:bg-gray-900 text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800')
                }
              >
                🌿 Patient Briefing
              </button>
            )}
          </div>

          {/* Report tab */}
          {activeTab === 'report' && (
            <div className="border border-gray-200 dark:border-gray-700 rounded-2xl p-5 bg-white dark:bg-gray-900 flex-1 overflow-auto max-h-96">
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-medium uppercase tracking-wide text-gray-400">Generated Report</span>
                <button
                  onClick={handleCopy}
                  className="text-xs px-3 py-1 rounded-lg bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
                >
                  {copied ? 'Copied!' : 'Copy'}
                </button>
              </div>
              <pre className="text-sm text-gray-800 dark:text-gray-200 leading-relaxed whitespace-pre-wrap font-sans">
                {result.report || 'No report generated.'}
              </pre>
            </div>
          )}

          {/* Briefing tab */}
          {activeTab === 'briefing' && briefing && (
            <div className="border border-teal-200 dark:border-teal-800 rounded-2xl p-5 bg-teal-50 dark:bg-teal-950 flex-1 overflow-auto max-h-96">
              <div className="flex items-center gap-2 mb-3">
                <span className="text-lg">🌿</span>
                <span className="text-xs font-medium uppercase tracking-wide text-teal-700 dark:text-teal-300">
                  Patient-Friendly Summary
                </span>
              </div>
              <p className="text-sm text-teal-900 dark:text-teal-100 leading-relaxed">
                {briefing}
              </p>
              <p className="mt-3 text-xs text-teal-600 dark:text-teal-400">
                This summary is written in plain language for non-medical readers.
              </p>
            </div>
          )}

          <div className="text-xs text-amber-700 dark:text-amber-400 bg-amber-50 dark:bg-amber-950 border border-amber-200 dark:border-amber-800 rounded-lg px-3 py-2">
            For research use only. Not for clinical diagnosis.
          </div>

          <div className="flex gap-3">
            <button
              onClick={() => navigate('/history')}
              className="flex-1 py-2 rounded-lg border border-gray-200 dark:border-gray-700 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
            >
              View history
            </button>
            <button
              onClick={() => navigate('/analyze')}
              className="flex-1 py-2 rounded-lg bg-teal-600 hover:bg-teal-700 text-white text-sm font-medium transition-colors"
            >
              New analysis
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
