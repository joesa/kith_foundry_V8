// @ts-nocheck
import { useState, useEffect } from 'react'
import './App.css'

function App() {
    const [dots, setDots] = useState('')
    const [showHint, setShowHint] = useState(false)

    useEffect(() => {
        const interval = setInterval(() => {
            setDots(d => d.length >= 3 ? '' : d + '.')
        }, 500)
        return () => clearInterval(interval)
    }, [])

    useEffect(() => {
        const timer = setTimeout(() => setShowHint(true), 2000)
        return () => clearTimeout(timer)
    }, [])

    return (
        <div className="kith-container">
            <div className="kith-glow" />
            <div className="kith-content">
                <div className="kith-logo">
                    <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
                        <rect width="48" height="48" rx="12" fill="url(#grad)" />
                        <path d="M14 14h6v6h-6zM22 14h6v6h-6zM14 22h6v6h-6zM28 22h6v6h-6zM22 28h6v6h-6zM28 28h6v6h-6z" fill="white" fillOpacity="0.9" />
                        <defs>
                            <linearGradient id="grad" x1="0" y1="0" x2="48" y2="48">
                                <stop stopColor="#6366F1" />
                                <stop offset="1" stopColor="#A855F7" />
                            </linearGradient>
                        </defs>
                    </svg>
                </div>
                <h1 className="kith-title">Kith Foundry</h1>
                <p className="kith-subtitle">Your app is being crafted{dots}</p>
                <div className="kith-loader">
                    <div className="kith-loader-bar" />
                </div>
                <p className={`kith-hint ${showHint ? 'visible' : ''}`}>
                    Describe what you want to build in the chat panel
                </p>
            </div>
            <div className="kith-footer">
                <span>Powered by AI</span>
                <span className="kith-dot">·</span>
                <span>Built with React + Vite</span>
            </div>
        </div>
    )
}

export default App
