import { useState } from 'react'
import { CircleAlert, CircleCheck } from 'lucide-react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router'
import { iniciarSesion } from '../../api/auth.js'
import { useSesion } from '../../auth/contexto.js'
import { RUTA_POR_ROL } from '../../auth/sesion.js'
import Campo from '../../components/Campo.jsx'
import LayoutAcceso from '../../components/LayoutAcceso.jsx'
import '../../components/formulario.css'
import './Login.css'

const VACIO = { correo: '', contrasena: '' }

function Login() {
  const { sesion, iniciar } = useSesion()
  const { state } = useLocation()
  const navigate = useNavigate()
  const [datos, setDatos] = useState(VACIO)
  const [errores, setErrores] = useState({})
  const [errorGeneral, setErrorGeneral] = useState('')
  const [enviando, setEnviando] = useState(false)

  if (sesion) {
    return <Navigate to={RUTA_POR_ROL[sesion.rol]} replace />
  }

  function cambiar(evento) {
    const { name, value } = evento.target
    setDatos((anteriores) => ({ ...anteriores, [name]: value }))
    setErrores((anteriores) => ({ ...anteriores, [name]: undefined }))
  }

  async function enviar(evento) {
    evento.preventDefault()
    setErrorGeneral('')

    // Con algún campo vacío no se continúa: se marca sin llamar a la API.
    const vacios = Object.fromEntries(
      Object.entries(datos)
        .filter(([, valor]) => !valor.trim())
        .map(([campo]) => [campo, 'Completá este campo.']),
    )
    if (Object.keys(vacios).length > 0) {
      setErrores(vacios)
      return
    }

    setEnviando(true)
    try {
      const nueva = await iniciarSesion(datos)
      iniciar(nueva)
      navigate(state?.desde ?? RUTA_POR_ROL[nueva.rol], { replace: true })
    } catch (error) {
      const campos = error.campos ?? {}
      setErrores(campos)
      if (Object.keys(campos).length === 0) setErrorGeneral(error.message)
      setDatos((anteriores) => ({ ...anteriores, contrasena: '' }))
    } finally {
      setEnviando(false)
    }
  }

  return (
    <LayoutAcceso
      panel={
        <>
          <h2>Cada servicio, asentado para siempre</h2>
          <p className="acceso-panel-texto">
            Los registros no se editan ni se eliminan. Si hay un error, se corrige con un
            nuevo registro vinculado al original.
          </p>
        </>
      }
      enlaceEncabezado={<Link to="/registro">Crear cuenta</Link>}
    >
      <div className="login">
        <h1 className="titulo-pagina">Iniciar sesión</h1>
        <p className="subtitulo-pagina">Ingresá con tu correo y contraseña.</p>

        {state?.registrado && !errorGeneral && (
          <p className="aviso aviso-exito" role="status">
            <CircleCheck size={18} aria-hidden="true" />
            Tu cuenta fue creada. Ya podés iniciar sesión.
          </p>
        )}
        {state?.solicitudEnviada && !errorGeneral && (
          <p className="aviso aviso-exito" role="status">
            <CircleCheck size={18} aria-hidden="true" />
            Recibimos tu solicitud de alta. Quedó pendiente de revisión: vas a poder iniciar
            sesión cuando un administrador la apruebe.
          </p>
        )}
        {errorGeneral && (
          <p className="aviso aviso-error" role="alert">
            <CircleAlert size={18} aria-hidden="true" />
            {errorGeneral}
          </p>
        )}

        <form onSubmit={enviar} noValidate>
          <Campo
            id="correo"
            etiqueta="Correo electrónico"
            type="email"
            autoComplete="email"
            inputMode="email"
            value={datos.correo}
            onChange={cambiar}
            error={errores.correo}
          />
          <Campo
            id="contrasena"
            etiqueta="Contraseña"
            type="password"
            autoComplete="current-password"
            value={datos.contrasena}
            onChange={cambiar}
            error={errores.contrasena}
            accesorio={<Link to="/recuperar">¿Olvidaste tu contraseña?</Link>}
          />

          <button type="submit" className="boton-primario" disabled={enviando}>
            {enviando ? 'Ingresando…' : 'Ingresar'}
          </button>
        </form>

        <p className="pie-formulario">
          ¿No tenés cuenta? <Link to="/registro">Creá una</Link>
        </p>
      </div>
    </LayoutAcceso>
  )
}

export default Login
