import { CircleCheck } from 'lucide-react'
import { Link, useLocation } from 'react-router'
import LayoutAcceso from '../../components/LayoutAcceso.jsx'
import '../../components/formulario.css'

// Provisoria: el formulario de inicio de sesión llega con la HU-002.
function Login() {
  const { state } = useLocation()

  return (
    <LayoutAcceso
      panel={
        <>
          <h2>Cada servicio, asentado para siempre</h2>
          <p>
            Los registros no se editan ni se eliminan. Si hay un error, se corrige con un
            nuevo registro vinculado al original.
          </p>
        </>
      }
      enlaceEncabezado={<Link to="/registro">Crear cuenta</Link>}
    >
      <h1 className="titulo-pagina">Iniciar sesión</h1>
      {state?.registrado && (
        <p className="aviso aviso-exito" role="status">
          <CircleCheck size={18} aria-hidden="true" />
          Tu cuenta fue creada. Ya podés iniciar sesión con tu correo y contraseña.
        </p>
      )}
      <p className="subtitulo-pagina">El inicio de sesión estará disponible próximamente.</p>
      <p className="pie-formulario">
        ¿No tenés cuenta? <Link to="/registro">Creá una</Link>
      </p>
    </LayoutAcceso>
  )
}

export default Login
