import { useEffect, useState } from 'react'
import { LogOut, Menu, X } from 'lucide-react'
import { NavLink, useNavigate } from 'react-router'
import { useSesion } from '../auth/contexto.js'
import Logo from './Logo.jsx'
import './LayoutPanel.css'

const NOMBRE_ROL = { propietario: 'Propietario', taller: 'Taller verificado', administrador: 'Administrador' }

// "Lucía" + "Fernández" → "LF". Las sesiones anteriores sin apellido usan las dos primeras letras.
function iniciales({ nombre, apellido }) {
  return (apellido ? nombre[0] + apellido[0] : nombre.slice(0, 2)).toUpperCase()
}

// Pantallas con sesión: barra lateral en escritorio; en el celular, barra superior con menú.
// `enlaces`: [{ a, texto, Icono, insignia? }]
function LayoutPanel({ enlaces, children }) {
  const { sesion, cerrar } = useSesion()
  const navigate = useNavigate()
  const [menuAbierto, setMenuAbierto] = useState(false)

  useEffect(() => {
    if (!menuAbierto) return
    const cerrarConEscape = (evento) => evento.key === 'Escape' && setMenuAbierto(false)
    document.addEventListener('keydown', cerrarConEscape)
    return () => document.removeEventListener('keydown', cerrarConEscape)
  }, [menuAbierto])

  function cerrarSesion() {
    cerrar()
    navigate('/login', { replace: true })
  }

  const nombreCompleto = [sesion.nombre, sesion.apellido].filter(Boolean).join(' ')
  const hayPendientes = enlaces.some((enlace) => enlace.insignia > 0)

  return (
    <div className="panel">
      <aside className={`panel-lateral ${menuAbierto ? 'abierto' : ''}`}>
        <div className="panel-barra">
          <button
            type="button"
            className="panel-boton-menu"
            aria-expanded={menuAbierto}
            aria-controls="panel-menu"
            aria-label={menuAbierto ? 'Cerrar menú' : 'Abrir menú'}
            onClick={() => setMenuAbierto((abierto) => !abierto)}
          >
            {menuAbierto ? <X size={24} aria-hidden="true" /> : <Menu size={24} aria-hidden="true" />}
            {hayPendientes && !menuAbierto && <span className="panel-boton-menu-aviso" />}
          </button>
          <Logo />
          <span className="panel-avatar panel-avatar-barra" aria-hidden="true">
            {iniciales(sesion)}
          </span>
        </div>

        <div id="panel-menu" className="panel-menu">
          <nav className="panel-nav" aria-label="Secciones">
            {enlaces.map(({ a, texto, Icono, insignia }) => (
              <NavLink key={a} to={a} end className="panel-nav-enlace" onClick={() => setMenuAbierto(false)}>
                <Icono size={20} aria-hidden="true" />
                <span>{texto}</span>
                {insignia > 0 && (
                  <span className="panel-insignia" aria-label={`${insignia} pendientes`}>
                    {insignia}
                  </span>
                )}
              </NavLink>
            ))}
          </nav>
          <div className="panel-usuario">
            <span className="panel-avatar" aria-hidden="true">
              {iniciales(sesion)}
            </span>
            <div>
              <strong>{nombreCompleto}</strong>
              <span>{NOMBRE_ROL[sesion.rol]}</span>
            </div>
          </div>
          <button type="button" className="panel-cerrar" onClick={cerrarSesion}>
            <LogOut size={20} aria-hidden="true" />
            <span>Cerrar sesión</span>
          </button>
        </div>
      </aside>
      {menuAbierto && <div className="panel-velo" aria-hidden="true" onClick={() => setMenuAbierto(false)} />}
      <main className="panel-contenido">{children}</main>
    </div>
  )
}

export default LayoutPanel
