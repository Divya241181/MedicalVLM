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
