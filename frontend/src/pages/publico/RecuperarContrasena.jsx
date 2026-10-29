import { useState } from 'react'
import { ChevronLeft, CircleAlert, Mail } from 'lucide-react'
import { Link, useNavigate, useSearchParams } from 'react-router'
import { recuperarContrasena, restablecerContrasena } from '../../api/auth.js'
import Campo from '../../components/Campo.jsx'
import LayoutAcceso from '../../components/LayoutAcceso.jsx'
import '../../components/formulario.css'
import './RecuperarContrasena.css'

// Paso 1: pedir el enlace. La respuesta es la misma exista o no la cuenta.
function PedirEnlace() {
  const [correo, setCorreo] = useState('')
  const [error, setError] = useState('')
  const [errorGeneral, setErrorGeneral] = useState('')
  const [mensaje, setMensaje] = useState('')
  const [enviando, setEnviando] = useState(false)

  async function enviar(evento) {
    evento.preventDefault()
    setErrorGeneral('')
    if (!correo.trim()) {
      setError('Completá este campo.')
      return
    }
    setEnviando(true)
    try {
      setMensaje((await recuperarContrasena(correo)).mensaje)
    } catch (e) {
      if (e.campos?.correo) setError(e.campos.correo)
      else setErrorGeneral(e.message)
    } finally {
      setEnviando(false)
    }
  }

  return (
    <section className="recuperar-tarjeta" aria-labelledby="titulo-recuperar">
      <span className="recuperar-paso">Paso 1</span>
      <h1 id="titulo-recuperar">Recuperar contraseña</h1>
      <p className="recuperar-texto">Ingresá el correo de tu cuenta y te enviaremos un enlace para restablecerla.</p>
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
          value={correo}
          onChange={(evento) => {
            setCorreo(evento.target.value)
            setError('')
          }}
          error={error}
        />
        <button type="submit" className="boton-primario" disabled={enviando}>
          {enviando ? 'Enviando…' : 'Enviar enlace'}
        </button>
      </form>
      {mensaje && (
        <p className="aviso aviso-exito recuperar-enviado" role="status">
          <Mail size={18} aria-hidden="true" />
          {mensaje}
        </p>
      )}
    </section>
  )
}

// Paso 2: desde el enlace del correo, crear la nueva contraseña.
function CrearContrasena({ token }) {
  const navigate = useNavigate()
  const [datos, setDatos] = useState({ contrasena: '', confirmacion: '' })
  const [errores, setErrores] = useState({})
  const [errorGeneral, setErrorGeneral] = useState('')
  const [enviando, setEnviando] = useState(false)

  function cambiar(evento) {
    const { name, value } = evento.target
    setDatos((anteriores) => ({ ...anteriores, [name]: value }))
    setErrores((anteriores) => ({ ...anteriores, [name]: undefined }))
  }

  async function enviar(evento) {
    evento.preventDefault()
    setErrorGeneral('')
    const faltantes = {}
    if (!datos.contrasena) faltantes.contrasena = 'Completá este campo.'
    if (!datos.confirmacion) faltantes.confirmacion = 'Completá este campo.'
    else if (datos.confirmacion !== datos.contrasena) faltantes.confirmacion = 'Las contraseñas no coinciden.'
    if (Object.keys(faltantes).length > 0) {
      setErrores(faltantes)
      return
    }
    setEnviando(true)
    try {
      await restablecerContrasena(token, datos.contrasena)
      navigate('/login', { replace: true, state: { contrasenaCambiada: true } })
    } catch (e) {
      if (e.campos?.contrasena) setErrores({ contrasena: e.campos.contrasena })
      else setErrorGeneral(e.message)
      setEnviando(false)
    }
  }

  return (
    <section className="recuperar-tarjeta" aria-labelledby="titulo-nueva">
      <span className="recuperar-paso">Paso 2 · Desde el enlace recibido</span>
      <h1 id="titulo-nueva">Crear nueva contraseña</h1>
      {errorGeneral && (
        <p className="aviso aviso-error" role="alert">
          <CircleAlert size={18} aria-hidden="true" />
          <span>
            {errorGeneral} <Link to="/recuperar">Pedí uno nuevo</Link>.
          </span>
        </p>
      )}
      <form onSubmit={enviar} noValidate>
        <Campo
          id="contrasena"
          etiqueta="Nueva contraseña"
          type="password"
          autoComplete="new-password"
          value={datos.contrasena}
          onChange={cambiar}
          error={errores.contrasena}
          ayuda="Mínimo 8 caracteres, con al menos una mayúscula y un número."
        />
        <Campo
          id="confirmacion"
          etiqueta="Confirmar contraseña"
          type="password"
          autoComplete="new-password"
          value={datos.confirmacion}
          onChange={cambiar}
          error={errores.confirmacion}
        />
        <button type="submit" className="boton-primario" disabled={enviando}>
          {enviando ? 'Guardando…' : 'Guardar contraseña'}
        </button>
      </form>
    </section>
  )
}

// Recuperación de contraseña (HU-015): /recuperar pide el enlace; /recuperar?token=… crea la nueva.
function RecuperarContrasena() {
  const [parametros] = useSearchParams()
  const token = parametros.get('token')

  return (
    <LayoutAcceso
      panel={
        <>
          <h2>Recuperá el acceso a tu cuenta</h2>
          <p>Te enviamos un enlace de un solo uso para que crees una nueva contraseña.</p>
        </>
      }
      enlaceEncabezado={<Link to="/login">Ingresar</Link>}
    >
      <Link className="recuperar-volver" to="/login">
        <ChevronLeft size={18} aria-hidden="true" />
        Volver a iniciar sesión
      </Link>
      {token ? <CrearContrasena token={token} /> : <PedirEnlace />}
    </LayoutAcceso>
  )
}

export default RecuperarContrasena
