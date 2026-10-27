import { LogOut } from 'lucide-react'
import { useNavigate } from 'react-router'
import { useSesion } from '../auth/contexto.js'
import Logo from './Logo.jsx'
import './PanelProvisorio.css'

// Vista provisoria de cada rol hasta que se implementen sus pantallas.
function PanelProvisorio({ titulo, descripcion }) {
  const { sesion, cerrar } = useSesion()
  const navigate = useNavigate()

  function cerrarSesion() {
    cerrar()
    navigate('/login', { replace: true })
  }

  return (
    <div className="panel-provisorio">
      <header className="panel-provisorio-encabezado">
        <Logo />
        <button type="button" className="boton-secundario" onClick={cerrarSesion}>
          <LogOut size={16} aria-hidden="true" />
          Cerrar sesión
        </button>
      </header>
      <main className="panel-provisorio-contenido">
        <p className="panel-provisorio-saludo">Hola, {sesion.nombre}</p>
        <h1 className="titulo-pagina">{titulo}</h1>
        <p className="subtitulo-pagina">{descripcion}</p>
      </main>
    </div>
  )
}

export default PanelProvisorio
