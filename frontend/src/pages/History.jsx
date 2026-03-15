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
