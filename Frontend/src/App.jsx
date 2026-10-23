import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  Activity, AirVent, ArrowUpRight, AudioLines, Check, ChevronDown, CircleHelp,
  Clock3, House, Lightbulb, Mic2, MoreHorizontal, Send, Settings2,
  ShieldCheck, Snowflake, Thermometer, Wifi,
} from 'lucide-react'

const API_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '')
const INITIAL_STATE = {
  living_room_light: 'off', thermostat_temp: 22, front_door: 'closed', air_conditioner: 'off',
}

const suggestions = ['Enciende la luz de la sala', 'Pon el termostato a 24 grados', 'Dame el estado de la casa']

function IconBox({ children, className = '' }) {
  return <span className={`icon-box ${className}`}>{children}</span>
}

function App() {
  const [home, setHome] = useState(INITIAL_STATE)
  const [messages, setMessages] = useState([
    { from: 'assistant', text: '¡Hola! Soy Alexa. ¿Qué te gustaría hacer en casa?', time: 'Ahora' },
  ])
  const [input, setInput] = useState('')
  const [connection, setConnection] = useState('connecting')
  const [sending, setSending] = useState(false)
  const [notice, setNotice] = useState('')
  const socketRef = useRef(null)
  const messagesEndRef = useRef(null)

  const activeDevices = useMemo(() =>
    Number(home.living_room_light === 'on') + Number(home.air_conditioner === 'on'), [home])
  const todayLabel = new Intl.DateTimeFormat('es', { weekday: 'long', day: 'numeric', month: 'long' })
    .format(new Date()).toLocaleUpperCase('es')

  const refreshStatus = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/api/status`)
      if (!response.ok) throw new Error('No se pudo consultar el estado')
      const data = await response.json()
      setHome((current) => ({ ...current, ...data.state }))
    } catch {
      // Keep the latest known state while the backend is unavailable.
    }
  }, [])

  useEffect(() => {
    refreshStatus()
    const wsUrl = API_URL.replace(/^http/, 'ws') + '/ws'
    let socket
    let retryTimer
    let disposed = false

    const connect = () => {
      if (disposed) return
      setConnection('connecting')
      socket = new WebSocket(wsUrl)
      socketRef.current = socket
      socket.onopen = () => setConnection('online')
      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          if (data.state) setHome((current) => ({ ...current, ...data.state }))
          if (data.response && data.response !== 'Conexión establecida.') {
            setMessages((current) => [...current, { from: 'assistant', text: data.response, time: 'Ahora' }])
            setSending(false)
          }
        } catch {
          setSending(false)
        }
      }
      socket.onclose = () => {
        setConnection('offline')
        if (!disposed) retryTimer = window.setTimeout(connect, 3000)
      }
      socket.onerror = () => socket.close()
    }
    connect()
    const poll = window.setInterval(refreshStatus, 15000)
    return () => {
      disposed = true
      window.clearInterval(poll)
      window.clearTimeout(retryTimer)
      socket?.close()
    }
  }, [refreshStatus])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const addMessage = (from, text) => setMessages((current) => [
    ...current,
    { from, text, time: new Intl.DateTimeFormat('es', { hour: '2-digit', minute: '2-digit' }).format(new Date()) },
  ])

  const sendCommand = (value = input) => {
    const text = value.trim()
    if (!text || sending) return
    addMessage('user', text)
    setInput('')
    setSending(true)
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ message: text }))
      window.setTimeout(() => setSending(false), 8000)
    } else {
      addMessage('assistant', 'No hay conexión con el asistente. Revisa que el backend esté activo e inténtalo de nuevo.')
      setSending(false)
    }
  }

  const toggleLight = () => sendCommand(home.living_room_light === 'on' ? 'Apaga la luz de la sala' : 'Enciende la luz de la sala')
  const changeTemp = (amount) => {
    const next = Math.min(35, Math.max(10, Number(home.thermostat_temp) + amount))
    sendCommand(`Pon el termostato a ${next} grados`)
  }

  const showNotice = (text) => {
    setNotice(text)
    window.setTimeout(() => setNotice(''), 2600)
  }

  const connectionLabel = connection === 'online' ? 'Conectado' : connection === 'connecting' ? 'Conectando…' : 'Sin conexión'

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="#inicio" aria-label="Smart Home, inicio">
          <span className="brand-mark"><House size={19} strokeWidth={2.5} /></span>
          <span>smart<span className="brand-light">home</span></span>
        </a>
        <div className="side-label">MENÚ PRINCIPAL</div>
        <nav className="navigation" aria-label="Navegación principal">
          <a className="nav-link selected" href="#inicio"><House size={18} /> <span>Inicio</span></a>
          <button className="nav-link" onClick={() => showNotice('La vista de habitaciones estará disponible pronto.')}><Activity size={18} /><span>Habitaciones</span><span className="nav-count">3</span></button>
          <button className="nav-link" onClick={() => showNotice('La automatización estará disponible pronto.')}><AudioLines size={18} /><span>Automatizaciones</span></button>
        </nav>
        <div className="side-label device-label">TUS DISPOSITIVOS <button onClick={() => showNotice('Puedes agregar dispositivos desde Configuración.')} aria-label="Agregar dispositivo">+</button></div>
        <nav className="navigation">
          <button className="nav-link" onClick={() => showNotice('Vista de iluminación seleccionada.')}><Lightbulb size={18} /><span>Iluminación</span><span className="nav-dot green" /></button>
          <button className="nav-link" onClick={() => showNotice('Vista de clima seleccionada.')}><Thermometer size={18} /><span>Climatización</span></button>
          <button className="nav-link" onClick={() => showNotice('Vista de seguridad seleccionada.')}><ShieldCheck size={18} /><span>Seguridad</span></button>
        </nav>
        <div className="sidebar-bottom">
          <div className="upgrade-card"><div className="upgrade-icon"><AudioLines size={17} /></div><strong>Tu hogar, más inteligente</strong><p>Controla todo con tu voz.</p><button onClick={() => showNotice('Alexa está lista para recibir tus comandos.')}>Hablar con Alexa <ArrowUpRight size={14} /></button></div>
          <button className="profile" onClick={() => showNotice('Perfil de usuario')}><span className="avatar">JD</span><span className="profile-info"><strong>Juan Delgado</strong><small>Administrador</small></span><MoreHorizontal size={19} /></button>
        </div>
      </aside>

      <main className="main-content" id="inicio">
        <header className="topbar">
          <div className="breadcrumb">Mi hogar <span>/</span> <strong>Inicio</strong></div>
          <div className="top-actions"><span className={`connection-pill ${connection}`}><span className="status-dot" />{connectionLabel}</span><button className="icon-button" aria-label="Ayuda" onClick={() => showNotice('Escribe un comando en el chat para controlar tu hogar.')}><CircleHelp size={19} /></button><button className="icon-button settings-button" aria-label="Configuración" onClick={() => showNotice(`Configura la conexión del backend en ${API_URL}`)}><Settings2 size={19} /></button><button className="home-picker" onClick={() => showNotice('Casa principal')}><span className="home-avatar"><House size={15} /></span><span>Casa principal</span><ChevronDown size={15} /></button></div>
        </header>

        <section className="welcome-row">
          <div><div className="eyebrow"><span className="eyebrow-line" /> {todayLabel}</div><h1>Buenos días, Juan <span className="wave">✳</span></h1><p className="welcome-copy">Aquí tienes un resumen de lo que pasa en tu hogar.</p></div>
          <div className="weather-card home-summary"><span className="weather-icon"><House size={20} /></span><div><strong>Tu hogar</strong><small>Casa principal</small></div><span className="weather-divider" /><div className="weather-extra"><small>{activeDevices} dispositivos activos</small><small>{connectionLabel}</small></div></div>
        </section>

        <section className="overview-grid" aria-label="Resumen del hogar">
          <article className="overview-card"><div className="overview-top"><span>Dispositivos activos</span><IconBox className="purple"><Activity size={18} /></IconBox></div><div className="overview-value">{activeDevices}<span> / 4</span></div><div className="overview-foot"><span className="trend"><ArrowUpRight size={14} /> Todo bajo control</span></div><div className="mini-bars"><i /><i /><i /><i /><i /><i /><i /><i /><i /><i /><i /><i /></div></article>
          <article className="overview-card"><div className="overview-top"><span>Temperatura interior</span><IconBox className="orange"><Thermometer size={18} /></IconBox></div><div className="overview-value">{home.thermostat_temp}<span>°C</span></div><div className="overview-foot"><span className="neutral-pill"><span /> Temperatura ideal</span></div><div className="temperature-track"><span /></div></article>
          <article className="overview-card"><div className="overview-top"><span>Seguridad</span><IconBox className="green"><ShieldCheck size={18} /></IconBox></div><div className="overview-value status-value"><span className="secure-check"><Check size={15} /></span> Protegida</div><div className="overview-foot"><span className="muted-foot"><span className="live-dot" /> Puerta principal {home.front_door === 'closed' ? 'cerrada' : 'abierta'}</span></div><div className="secure-line"><i /><i /><i /><i /><i /><i /><i /><i /><i /><i /><i /><i /></div></article>
        </section>

        <section className="section-heading"><div><h2>Dispositivos</h2><p>Administra los dispositivos de tu hogar</p></div><button className="text-button" onClick={() => showNotice('Mostrando todos tus dispositivos')}>Ver todos <ArrowUpRight size={15} /></button></section>
        <section className="device-grid">
          <article className={`device-card light-card ${home.living_room_light === 'on' ? 'device-on' : ''}`}>
            <div className="device-card-top"><IconBox className={home.living_room_light === 'on' ? 'yellow' : 'soft'}><Lightbulb size={20} /></IconBox><button className="dots-button" aria-label="Opciones de luz" onClick={() => showNotice('Luz de la sala')}><MoreHorizontal size={20} /></button></div>
            <div className="device-name-row"><div><h3>Luz de la sala</h3><p>Sala de estar · Philips Hue</p></div><button className={`toggle ${home.living_room_light === 'on' ? 'on' : ''}`} aria-label={home.living_room_light === 'on' ? 'Apagar luz' : 'Encender luz'} aria-pressed={home.living_room_light === 'on'} onClick={toggleLight}><span /></button></div>
            <div className="device-card-footer"><span><span className={`device-state-dot ${home.living_room_light}`} />{home.living_room_light === 'on' ? 'Encendida' : 'Apagada'}</span><span>{home.living_room_light === 'on' ? 'Brillo 80%' : 'Lista para usar'}</span></div>
          </article>
          <article className="device-card climate-card">
            <div className="device-card-top"><IconBox className="blue"><Thermometer size={20} /></IconBox><button className="dots-button" aria-label="Opciones de termostato" onClick={() => showNotice('Termostato del hogar')}><MoreHorizontal size={20} /></button></div>
            <div className="thermostat-row"><div><h3>Termostato</h3><p>Clima interior · Automático</p></div><div className="temp-control"><button onClick={() => changeTemp(-1)} aria-label="Bajar temperatura">−</button><span>{home.thermostat_temp}°</span><button onClick={() => changeTemp(1)} aria-label="Subir temperatura">+</button></div></div>
            <div className="device-card-footer"><span><span className="device-state-dot blue-dot" />Modo automático</span><span><Snowflake size={13} /> Enfriando</span></div>
          </article>
          <article className="device-card compact-card">
            <div className="device-card-top"><IconBox className="cyan"><AirVent size={20} /></IconBox><span className="device-tag">CLIMA</span></div>
            <h3>Aire acondicionado</h3><p>Sala de estar</p><div className="compact-status"><span className="device-state-dot off" />{home.air_conditioner === 'on' ? 'Encendido' : 'Apagado'}<span className="compact-temp">24°</span></div>
          </article>
          <article className="device-card compact-card security-card">
            <div className="device-card-top"><IconBox className="green"><ShieldCheck size={20} /></IconBox><span className="device-tag">SEGURIDAD</span></div>
            <h3>Puerta principal</h3><p>Entrada · Sensor inteligente</p><div className="compact-status"><span className="device-state-dot green-dot" />{home.front_door === 'closed' ? 'Cerrada y asegurada' : 'Abierta'}</div>
          </article>
        </section>

        <section className="bottom-grid">
          <article className="activity-panel"><div className="panel-heading"><div><h2>Actividad reciente</h2><p>Lo último que pasó en tu hogar</p></div><button className="dots-button" aria-label="Más actividad" onClick={() => showNotice('Mostrando actividad reciente')}><MoreHorizontal size={20} /></button></div><div className="activity-list"><div className="activity-item"><span className="activity-icon light-activity"><Lightbulb size={16} /></span><div><strong>Luz de la sala apagada</strong><small>Por Alexa · Sala de estar</small></div><time>hace 12 min</time></div><div className="activity-item"><span className="activity-icon temp-activity"><Thermometer size={16} /></span><div><strong>Termostato ajustado a {home.thermostat_temp}°C</strong><small>Por Juan · Clima interior</small></div><time>hace 1 h</time></div><div className="activity-item"><span className="activity-icon lock-activity"><ShieldCheck size={16} /></span><div><strong>Puerta principal asegurada</strong><small>Sistema de seguridad</small></div><time>hace 3 h</time></div></div></article>
          <article className="assistant-panel"><div className="assistant-heading"><div className="assistant-brand-icon"><AudioLines size={19} /></div><div><h2>Habla con Alexa</h2><p><span className="live-dot" /> Tu asistente está listo</p></div><button className="assistant-more" aria-label="Opciones del asistente" onClick={() => showNotice('Asistente Alexa conectado al hogar')}><MoreHorizontal size={20} /></button></div><div className="chat-messages" role="log" aria-live="polite">{messages.slice(-5).map((message, index) => <div className={`chat-line ${message.from}`} key={`${message.time}-${index}`}><span className="chat-avatar">{message.from === 'assistant' ? <AudioLines size={13} /> : 'JD'}</span><div className="bubble-wrap"><div className="chat-bubble">{message.text}</div><small>{message.time}</small></div></div>)}{sending && <div className="typing"><span /><span /><span /> Alexa está pensando</div>}<div ref={messagesEndRef} /></div><div className="suggestion-list">{suggestions.slice(0, 2).map((suggestion) => <button key={suggestion} onClick={() => sendCommand(suggestion)}>{suggestion}<ArrowUpRight size={12} /></button>)}</div><form className="chat-form" onSubmit={(event) => { event.preventDefault(); sendCommand() }}><input value={input} onChange={(event) => setInput(event.target.value)} placeholder="Escribe un comando…" aria-label="Comando para Alexa" /><button className="mic-button" type="button" aria-label="Voz no disponible" onClick={() => showNotice('El control por voz estará disponible pronto.')}><Mic2 size={17} /></button><button className="send-button" type="submit" aria-label="Enviar comando" disabled={!input.trim() || sending}><Send size={16} /></button></form><div className="voice-caption"><Wifi size={12} /> Prueba: “enciende la luz de la sala”</div></article>
        </section>
        <footer className="page-footer"><span><span className={`status-dot ${connection}`} /> {connectionLabel} · Smart Home API</span><span><Clock3 size={13} /> Última actualización hace unos segundos</span></footer>
      </main>
      {notice && <div className="toast" role="status">{notice}<button onClick={() => setNotice('')} aria-label="Cerrar aviso">×</button></div>}
    </div>
  )
}

export default App
