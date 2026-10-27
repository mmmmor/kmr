import { Link } from 'react-router'
import Logo from './Logo.jsx'
import './LayoutAcceso.css'

// Pantallas de acceso (registro, login, recuperación): panel verde a la izquierda
// en escritorio y encabezado simple en el celular.
function LayoutAcceso({ panel, enlaceEncabezado, children }) {
  return (
    <div className="acceso">
      <aside className="acceso-panel">
        <Logo invertido />
        <div className="acceso-panel-contenido">{panel}</div>
        <p className="acceso-panel-pie">
          ¿Querés consultar un vehículo? No necesitás cuenta.{' '}
          <Link to="/">Ir a la consulta pública</Link>
        </p>
      </aside>

      <header className="acceso-encabezado">
        <Logo />
        {enlaceEncabezado}
      </header>

      <main className="acceso-principal">
        <div className="acceso-formulario">{children}</div>
      </main>
    </div>
  )
}

export default LayoutAcceso
