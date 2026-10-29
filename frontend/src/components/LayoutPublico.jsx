import { Link } from 'react-router'
import { useSesion } from '../auth/contexto.js'
import { RUTA_POR_ROL } from '../auth/sesion.js'
import BuscadorDominio from './BuscadorDominio.jsx'
import Logo from './Logo.jsx'
import './LayoutPublico.css'

// Pantallas sin sesión (inicio y resultado de la consulta). `dominio`: si viene, el encabezado
// suma un buscador con ese dominio para hacer otra consulta sin volver al inicio.
function LayoutPublico({ dominio, children }) {
  const { sesion } = useSesion()
  const conBuscador = dominio !== undefined

  return (
    <div className="publico">
      <header className="publico-encabezado">
        <div className="publico-encabezado-contenido">
          <Logo />
          {conBuscador && (
            <div className="publico-buscador">
              <BuscadorDominio key={dominio} variante="compacto" inicial={dominio} />
            </div>
          )}
          <nav className="publico-nav" aria-label="Principal">
            {!conBuscador && (
              <>
                <a className="publico-enlace" href="#como-funciona">
                  Cómo funciona
                </a>
                <Link className="publico-enlace" to="/registro?tipo=taller">
                  Soy taller
                </Link>
              </>
            )}
            {sesion ? (
              <Link className="boton-primario boton-ajustado" to={RUTA_POR_ROL[sesion.rol]}>
                Ir a mi panel
              </Link>
            ) : (
              <>
                <Link className="publico-enlace publico-ingresar" to="/login">
                  <span className="texto-escritorio">Iniciar sesión</span>
                  <span className="texto-movil">Ingresar</span>
                </Link>
                <Link className="boton-primario boton-ajustado publico-crear-cuenta" to="/registro">
                  Crear cuenta
                </Link>
              </>
            )}
          </nav>
        </div>
      </header>
      <main className="publico-contenido">{children}</main>
    </div>
  )
}

export default LayoutPublico
