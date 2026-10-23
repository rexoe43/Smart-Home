import React from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.jsx'
import './styles.css'

class RenderBoundary extends React.Component {
  state = { error: null }

  static getDerivedStateFromError(error) {
    return { error }
  }

  componentDidCatch(error) {
    console.error('No se pudo mostrar el panel Smart Home:', error)
  }

  render() {
    if (this.state.error) {
      return (
        <main style={{ margin: '48px auto', maxWidth: 680, padding: 24, fontFamily: 'sans-serif' }}>
          <h1>Ocurrió un error al cargar Smart Home</h1>
          <p>Actualiza la página. Si vuelve a ocurrir, comparte este mensaje:</p>
          <pre style={{ whiteSpace: 'pre-wrap', color: '#a33' }}>{this.state.error.stack || this.state.error.message}</pre>
        </main>
      )
    }
    return this.props.children
  }
}

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <RenderBoundary>
      <App />
    </RenderBoundary>
  </React.StrictMode>,
)
