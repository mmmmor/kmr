import { Link } from 'react-router'
import LayoutAcceso from '../../components/LayoutAcceso.jsx'
import '../../components/formulario.css'

// Provisoria: la recuperación de contraseña llega con la HU-015.
function RecuperarContrasena() {
  return (
    <LayoutAcceso
      panel={<h2>Recuperá el acceso a tu cuenta</h2>}
      enlaceEncabezado={<Link to="/login">Ingresar</Link>}
    >
      <h1 className="titulo-pagina">Recuperar contraseña</h1>
      <p className="subtitulo-pagina">La recuperación de contraseña estará disponible próximamente.</p>
      <p className="pie-formulario">
        <Link to="/login">Volver a iniciar sesión</Link>
      </p>
    </LayoutAcceso>
  )
}

export default RecuperarContrasena
