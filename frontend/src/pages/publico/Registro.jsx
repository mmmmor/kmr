import { useState } from 'react'
import { Car, CircleAlert, Store, Wrench } from 'lucide-react'
import { Link, useNavigate } from 'react-router'
import { registrarPropietario } from '../../api/auth.js'
import Campo from '../../components/Campo.jsx'
import LayoutAcceso from '../../components/LayoutAcceso.jsx'
import '../../components/formulario.css'
import './Registro.css'

const VACIO = { nombre: '', apellido: '', correo: '', contrasena: '' }

function PanelRegistro() {
  return (
    <>
      <h2>El historial de tu vehículo, verificable y permanente</h2>
      <div className="registro-beneficio">
        <span className="registro-beneficio-icono">
          <Car size={18} aria-hidden="true" />
        </span>
        <div>
          <strong>Propietarios</strong>
          <p>
            Vinculá tus vehículos, autorizá a cada taller con un código temporal y
            recibí alertas de servicio.
          </p>
        </div>
      </div>
      <div className="registro-beneficio">
        <span className="registro-beneficio-icono">
          <Wrench size={18} aria-hidden="true" />
        </span>
        <div>
          <strong>Talleres</strong>
          <p>
            Registrá los servicios que realizás. Tu cuenta se habilita cuando un
            administrador verifica el establecimiento.
          </p>
        </div>
      </div>
    </>
  )
}

function Registro() {
  const navigate = useNavigate()
  const [datos, setDatos] = useState(VACIO)
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
    setEnviando(true)
    setErrorGeneral('')
    try {
      await registrarPropietario(datos)
      navigate('/login', { state: { registrado: true } })
    } catch (error) {
      const campos = error.campos ?? {}
      setErrores(campos)
      if (error.estado === 409) {
        setErrores({ correo: error.message })
      } else if (Object.keys(campos).length === 0) {
        setErrorGeneral(error.message)
      }
    } finally {
      setEnviando(false)
    }
  }

  return (
    <LayoutAcceso panel={<PanelRegistro />} enlaceEncabezado={<Link to="/login">Ingresar</Link>}>
      <h1 className="titulo-pagina">Crear cuenta</h1>
      <p className="subtitulo-pagina">Elegí cómo vas a usar KmR.</p>

      <div className="registro-tipo" role="group" aria-label="Tipo de cuenta">
        <button type="button" className="registro-tipo-opcion activa" aria-pressed="true">
          <Car size={18} aria-hidden="true" />
          Soy propietario
        </button>
        {/* El alta de talleres llega con la HU-003: la opción se ve pero no se puede elegir. */}
        <button
          type="button"
          className="registro-tipo-opcion"
          aria-pressed="false"
          aria-describedby="registro-taller-pronto"
          disabled
        >
          <Store size={18} aria-hidden="true" />
          Soy taller
        </button>
      </div>
      <p id="registro-taller-pronto" className="registro-tipo-nota">
        El alta de talleres estará disponible próximamente.
      </p>

      {errorGeneral && (
        <p className="aviso aviso-error" role="alert">
          <CircleAlert size={18} aria-hidden="true" />
          {errorGeneral}
        </p>
      )}

      <form onSubmit={enviar} noValidate>
        <p className="seccion-formulario">Datos personales</p>
        <div className="fila-campos">
          <Campo
            id="nombre"
            etiqueta="Nombre"
            autoComplete="given-name"
            value={datos.nombre}
            onChange={cambiar}
            error={errores.nombre}
          />
          <Campo
            id="apellido"
            etiqueta="Apellido"
            autoComplete="family-name"
            value={datos.apellido}
            onChange={cambiar}
            error={errores.apellido}
          />
        </div>
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
          autoComplete="new-password"
          value={datos.contrasena}
          onChange={cambiar}
          error={errores.contrasena}
          ayuda="Mínimo 8 caracteres, con al menos una mayúscula y un número."
        />

        <button type="submit" className="boton-primario" disabled={enviando}>
          {enviando ? 'Creando cuenta…' : 'Crear cuenta'}
        </button>
      </form>

      <p className="pie-formulario">
        ¿Ya tenés cuenta? <Link to="/login">Iniciá sesión</Link>
      </p>
    </LayoutAcceso>
  )
}

export default Registro
