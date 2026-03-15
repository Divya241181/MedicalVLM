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
