import { useState } from 'react'
import { Car, CircleAlert, Clock, Store, Wrench } from 'lucide-react'
import { Link, useNavigate, useSearchParams } from 'react-router'
import { registrarPropietario } from '../../api/auth.js'
import { solicitarAltaTaller } from '../../api/talleres.js'
import Campo from '../../components/Campo.jsx'
import LayoutAcceso from '../../components/LayoutAcceso.jsx'
import { formatearCuit, posicionTrasDigitos, soloDigitos } from '../../utils/cuit.js'
import '../../components/formulario.css'
import './Registro.css'

const VACIO = {
  nombre: '',
  apellido: '',
  correo: '',
  contrasena: '',
  razon_social: '',
  cuit: '',
  telefono: '',
  domicilio: '',
}

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
  const [parametros] = useSearchParams()
  const [tipo, setTipo] = useState(parametros.get('tipo') === 'taller' ? 'taller' : 'propietario')
  const esTaller = tipo === 'taller'
  const [datos, setDatos] = useState(VACIO)
  const [errores, setErrores] = useState({})
  const [errorGeneral, setErrorGeneral] = useState('')
  const [enviando, setEnviando] = useState(false)

  function cambiar(evento) {
    const { name, value } = evento.target
    setDatos((anteriores) => ({ ...anteriores, [name]: value }))
    setErrores((anteriores) => ({ ...anteriores, [name]: undefined }))
  }

  // El CUIT se tipea solo con números: los guiones se agregan solos y el cursor queda donde estaba.
  function cambiarCuit(evento) {
    const input = evento.target
    const anterior = datos.cuit
    let digitos = soloDigitos(input.value)
    let digitosAntesDelCursor = soloDigitos(input.value.slice(0, input.selectionStart)).length

    // Si se borró un guion, se borra también el dígito anterior; si no, el borrado quedaría trabado.
    if (digitos === soloDigitos(anterior) && input.value.length < anterior.length && digitosAntesDelCursor > 0) {
      digitos = digitos.slice(0, digitosAntesDelCursor - 1) + digitos.slice(digitosAntesDelCursor)
      digitosAntesDelCursor -= 1
    }

    const cuit = formatearCuit(digitos)
    setDatos((anteriores) => ({ ...anteriores, cuit }))
    setErrores((anteriores) => ({ ...anteriores, cuit: undefined }))
    requestAnimationFrame(() => {
      const posicion = posicionTrasDigitos(cuit, Math.min(digitosAntesDelCursor, 11))
      input.setSelectionRange(posicion, posicion)
    })
  }

  async function enviar(evento) {
    evento.preventDefault()
    setEnviando(true)
    setErrorGeneral('')
    try {
      if (esTaller) {
        await solicitarAltaTaller(datos)
        navigate('/login', { state: { solicitudEnviada: true } })
      } else {
        await registrarPropietario(datos)
        navigate('/login', { state: { registrado: true } })
      }
    } catch (error) {
      const campos = error.campos ?? {}
      setErrores(campos)
      if (Object.keys(campos).length === 0) setErrorGeneral(error.message)
    } finally {
      setEnviando(false)
    }
  }

  function elegirTipo(nuevo) {
    setTipo(nuevo)
    setErrores({})
    setErrorGeneral('')
  }

  const textoBoton = esTaller
    ? enviando ? 'Enviando solicitud…' : 'Enviar solicitud de alta'
    : enviando ? 'Creando cuenta…' : 'Crear cuenta'

  return (
    <LayoutAcceso panel={<PanelRegistro />} enlaceEncabezado={<Link to="/login">Ingresar</Link>}>
      <h1 className="titulo-pagina">Crear cuenta</h1>
      <p className="subtitulo-pagina">Elegí cómo vas a usar KmR.</p>

      <div className="registro-tipo" role="group" aria-label="Tipo de cuenta">
        <button
          type="button"
          className={`registro-tipo-opcion ${esTaller ? '' : 'activa'}`}
          aria-pressed={!esTaller}
          onClick={() => elegirTipo('propietario')}
        >
          <Car size={18} aria-hidden="true" />
          Soy propietario
        </button>
        <button
          type="button"
          className={`registro-tipo-opcion ${esTaller ? 'activa' : ''}`}
          aria-pressed={esTaller}
          onClick={() => elegirTipo('taller')}
        >
          <Store size={18} aria-hidden="true" />
          Soy taller
        </button>
      </div>

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

        {esTaller && (
          <>
            <p className="seccion-formulario">Datos del establecimiento</p>
            <Campo
              id="razon_social"
              etiqueta="Razón social"
              autoComplete="organization"
              value={datos.razon_social}
              onChange={cambiar}
              error={errores.razon_social}
            />
            <div className="fila-campos">
              <Campo
                id="cuit"
                etiqueta="CUIT"
                className="campo-mono"
                inputMode="numeric"
                maxLength={13}
                placeholder="30-71589234-7"
                ayuda="Solo números: los guiones se agregan solos."
                value={datos.cuit}
                onChange={cambiarCuit}
                error={errores.cuit}
              />
              <Campo
                id="telefono"
                etiqueta="Teléfono"
                type="tel"
                autoComplete="tel"
                value={datos.telefono}
                onChange={cambiar}
                error={errores.telefono}
              />
            </div>
            <Campo
              id="domicilio"
              etiqueta="Domicilio"
              autoComplete="street-address"
              value={datos.domicilio}
              onChange={cambiar}
              error={errores.domicilio}
            />

            <p className="aviso aviso-exito">
              <Clock size={18} aria-hidden="true" />
              <span>
                Tu solicitud quedará <strong>pendiente</strong> hasta que un administrador
                verifique el establecimiento. Vas a poder iniciar sesión una vez aprobada.
              </span>
            </p>
          </>
        )}

        <button type="submit" className="boton-primario" disabled={enviando}>
          {textoBoton}
        </button>
      </form>

      <p className="pie-formulario">
        ¿Ya tenés cuenta? <Link to="/login">Iniciá sesión</Link>
      </p>
    </LayoutAcceso>
  )
}

export default Registro
