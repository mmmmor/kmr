import { LogOut } from 'lucide-react'
import { NavLink, useNavigate } from 'react-router'
import { useSesion } from '../auth/contexto.js'
import Logo from './Logo.jsx'
import './LayoutPanel.css'

const NOMBRE_ROL = { propietario: 'Propietario', taller: 'Taller', administrador: 'Administrador' }

// Pantallas con sesión: barra lateral en escritorio, barra superior en el celular.
// `enlaces`: [{ a, texto, Icono, insignia? }]
function LayoutPanel({ enlaces, children }) {
  const { sesion, cerrar } = useSesion()
  const navigate = useNavigate()

  function cerrarSesion() {
    cerrar()
    navigate('/login', { replace: true })
  }

  const iniciales = sesion.nombre.slice(0, 2).toUpperCase()

  return (
    <div className="panel">
      <aside className="panel-lateral">
        <Logo />
        <nav className="panel-nav" aria-label="Secciones">
          {enlaces.map(({ a, texto, Icono, insignia }) => (
            <NavLink key={a} to={a} end className="panel-nav-enlace">
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
            {iniciales}
          </span>
          <div>
            <strong>{sesion.nombre}</strong>
            <span>{NOMBRE_ROL[sesion.rol]}</span>
          </div>
        </div>
        <button type="button" className="panel-cerrar" onClick={cerrarSesion}>
          <LogOut size={20} aria-hidden="true" />
          <span>Cerrar sesión</span>
        </button>
      </aside>
      <main className="panel-contenido">{children}</main>
    </div>
  )
}

export default LayoutPanel
