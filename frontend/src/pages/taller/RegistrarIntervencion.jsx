import { useState } from 'react'
import { CircleCheck, Plus, TriangleAlert } from 'lucide-react'
import { Link } from 'react-router'
import LayoutPanel from '../../components/LayoutPanel.jsx'
import Pasos from '../../components/Pasos.jsx'
import Patente from '../../components/Patente.jsx'
import { useFormularioIntervencion } from '../../components/intervencion/useFormularioIntervencion.js'
import { formatearFecha, formatearFechaHora } from '../../utils/fechas.js'
import { formatearMiles, textoAlertaKilometraje } from '../../utils/intervenciones.js'
import { ENLACES_TALLER } from './navegacion.js'
import PasoAutorizacion from './PasoAutorizacion.jsx'
import PasoDatos from './PasoDatos.jsx'
import '../../components/formulario.css'
import './RegistrarIntervencion.css'

const PASOS = ['Autorización', 'Datos del servicio', 'Confirmación']

function PasoConfirmacion({ intervencion, alRegistrarOtra }) {
  const cantidadItems = intervencion.items.length
  return (
    <section className="tarjeta-intervencion confirmacion" aria-labelledby="titulo-confirmacion">
      <span className="confirmacion-icono">
        <CircleCheck size={36} aria-hidden="true" />
      </span>
      <h2 id="titulo-confirmacion">Intervención registrada</h2>
      <p>
        Quedó asentada en el historial del vehículo con la identificación de tu taller. No se puede editar ni
        eliminar.
      </p>
      {intervencion.alerta_kilometraje && (
        <p className="aviso aviso-ambar confirmacion-alerta" role="status">
          <TriangleAlert size={18} aria-hidden="true" />
          <span>
            <strong>{textoAlertaKilometraje(intervencion.alerta_kilometraje)}.</strong> Quedó registrada con una
            alerta de inconsistencia visible en el historial. Si fue un error de carga, registrá una corrección
            vinculada.
          </span>
        </p>
      )}
      <div className="confirmacion-vehiculo">
        <Patente dominio={intervencion.dominio} tamano="chico" />
        <strong>{intervencion.tipo}</strong>
      </div>
      <dl className="confirmacion-datos">
        <div>
          <dt>Fecha del servicio</dt>
          <dd>{formatearFecha(intervencion.fecha_intervencion)}</dd>
        </div>
        <div>
          <dt>Kilometraje</dt>
          <dd className={`mono ${intervencion.alerta_kilometraje ? 'km-alerta' : ''}`}>
            {formatearMiles(intervencion.kilometraje)} km
          </dd>
        </div>
        <div>
          <dt>Insumos y trabajos</dt>
          <dd>
            {cantidadItems} {cantidadItems === 1 ? 'ítem' : 'ítems'}
          </dd>
        </div>
        <div>
          <dt>Comprobante</dt>
          <dd>{intervencion.tiene_comprobante ? 'Adjunto' : 'Sin comprobante'}</dd>
        </div>
        <div>
          <dt>Registrada el</dt>
          <dd>{formatearFechaHora(intervencion.fecha_registro)}</dd>
        </div>
      </dl>
      <p className="confirmacion-nota">
        El código del propietario quedó utilizado: para otra intervención va a necesitar uno nuevo.
      </p>
      <div className="confirmacion-acciones">
        <button type="button" className="boton-primario boton-ajustado" onClick={alRegistrarOtra}>
          <Plus size={18} aria-hidden="true" />
          Registrar otra intervención
        </button>
        <Link className="boton-secundario" to="/taller/registros">
          Ver registros realizados
        </Link>
      </div>
    </section>
  )
}

// Registro de una intervención por el taller en 3 pasos: Autorización → Datos del servicio → Confirmación (HU-007).
function RegistrarIntervencion() {
  const formulario = useFormularioIntervencion()
  const [paso, setPaso] = useState(0)
  const [autorizacion, setAutorizacion] = useState(null)
  const [errorCodigo, setErrorCodigo] = useState('')
  const [registrada, setRegistrada] = useState(null)

  function irAlPaso(numero) {
    setPaso(numero)
    window.scrollTo({ top: 0 })
  }

  function alAutorizar(nueva) {
    // Los datos ya cargados solo se conservan si es el mismo vehículo (por ejemplo, con un código nuevo).
    if (autorizacion?.vehiculo.dominio !== nueva.vehiculo.dominio) formulario.reiniciar()
    setAutorizacion(nueva)
    setErrorCodigo('')
    irAlPaso(1)
  }

  function cancelar() {
    formulario.reiniciar()
    setAutorizacion(null)
    setErrorCodigo('')
    irAlPaso(0)
  }

  function alRechazarCodigo(mensaje) {
    setErrorCodigo(`${mensaje} Pedile al propietario un código nuevo: los datos que cargaste se conservan.`)
    irAlPaso(0)
  }

  function alRegistrar(intervencion) {
    setRegistrada(intervencion)
    irAlPaso(2)
  }

  function registrarOtra() {
    formulario.reiniciar()
    setAutorizacion(null)
    setRegistrada(null)
    irAlPaso(0)
  }

  return (
    <LayoutPanel enlaces={ENLACES_TALLER}>
      <h1 className="titulo-pagina">Registrar intervención</h1>
      {paso === 0 && (
        <p className="subtitulo-pagina">
          Necesitás el dominio del vehículo y el código de autorización que te dio el propietario.
        </p>
      )}
      <Pasos pasos={PASOS} actual={paso} />

      {paso === 0 && (
        <PasoAutorizacion
          dominioInicial={autorizacion?.vehiculo.dominio}
          errorCodigo={errorCodigo}
          alAutorizar={alAutorizar}
        />
      )}
      {paso === 1 && (
        <PasoDatos
          autorizacion={autorizacion}
          formulario={formulario}
          alRegistrar={alRegistrar}
          alCancelar={cancelar}
          alRechazarCodigo={alRechazarCodigo}
        />
      )}
      {paso === 2 && <PasoConfirmacion intervencion={registrada} alRegistrarOtra={registrarOtra} />}
    </LayoutPanel>
  )
}

export default RegistrarIntervencion
