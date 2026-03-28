import { useEffect, useState } from 'react'
import './App.css'

function App() {
    const [dots, setDots] = useState('')

    useEffect(() => {
        const interval = setInterval(() => {
            setDots(d => (d.length >= 3 ? '' : d + '.'))
        }, 500)
        return () => clearInterval(interval)
    }, [])

    return (
        <main className="preview-shell" role="main">
            <h1 className="preview-title">Preview Ready</h1>
            <p className="preview-subtitle">Waiting for generated app files{dots}</p>
        </main>
    )
}

export default App
