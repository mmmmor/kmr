import { useEffect, useState } from 'react'
import { Check, CircleAlert, CircleCheck, FileText, User } from 'lucide-react'
import { Link, useSearchParams } from 'react-router'
import { listarVehiculos, registrarIntervencionPropia } from '../../api/vehiculos.js'
import Badge from '../../components/Badge.jsx'
import LayoutPanel from '../../components/LayoutPanel.jsx'
import SelectorVehiculo from '../../components/SelectorVehiculo.jsx'
import {
  CampoComprobante,
  CamposProximaRevision,
  CamposServicio,
  ListaItems,
} from '../../components/intervencion/SeccionesIntervencion.jsx'
import {
  mostrarPrimerError,
  useFormularioIntervencion,
} from '../../components/intervencion/useFormularioIntervencion.js'
import { formatearDominio } from '../../utils/dominio.js'
import { formatearMiles } from '../../utils/intervenciones.js'
import { ENLACES_PROPIETARIO } from './navegacion.js'
import '../../components/formulario.css'
import './IntervencionPropia.css'

const TENE_EN_CUENTA = [
  'Una vez registrada, la intervención no se puede editar ni eliminar.',
  'Adjuntar el comprobante le da más confianza a quien consulte el historial.',
]

// "aaaa-mm-dd" del formulario → "dd/mm/aaaa"
function fechaDelFormulario(valor) {
  const [anio, mes, dia] = valor.split('-')
  return `${dia}/${mes}/${anio}`
}

// Cómo se va a ver el registro en el historial, a medida que se completa el formulario.
function VistaPrevia({ formulario }) {
  const { datos, comprobante } = formulario
  return (
    <aside className="tarjeta-lateral vista-previa" aria-label="Vista previa">
      <h2>Así se va a ver en el historial</h2>
      <div className="vista-previa-registro">
        <div className="vista-previa-encabezado">
          <span>{datos.fecha_intervencion ? fechaDelFormulario(datos.fecha_intervencion) : 'Fecha'}</span>
          <strong className="mono">{datos.kilometraje ? `${formatearMiles(datos.kilometraje)} km` : '— km'}</strong>
        </div>
        <p className="vista-previa-tipo">{datos.tipo || 'Tipo de intervención'}</p>
        <div className="vista-previa-badges">
          <Badge Icono={User}>Autorreportado por el propietario</Badge>
          {comprobante && <Badge Icono={FileText}>Con comprobante de insumos</Badge>}
        </div>
      </div>
    </aside>
  )
}

// Intervención que el propietario hizo por su cuenta o que no registró un taller (HU-008).
function IntervencionPropia() {
  const formulario = useFormularioIntervencion()
  const [parametros, setParametros] = useSearchParams()
  const [vehiculos, setVehiculos] = useState(null)
  const [error, setError] = useState('')
  const [aviso, setAviso] = useState('')
  const [enviando, setEnviando] = useState(false)

  useEffect(() => {
    let vigente = true
    listarVehiculos()
      .then((lista) => vigente && setVehiculos(lista))
      .catch((e) => vigente && setError(e.message))
    return () => {
      vigente = false
    }
  }, [])

  const pedido = parametros.get('vehiculo')
  const vehiculo = vehiculos?.find((v) => v.id === pedido) ?? vehiculos?.[0]

  async function enviar(evento) {
    evento.preventDefault()
    setError('')
    setAviso('')
    if (!formulario.validar()) {
      mostrarPrimerError()
      return
    }

    setEnviando(true)
    try {
      const registrada = await registrarIntervencionPropia(vehiculo.id, formulario.aEntrada(), formulario.comprobante)
      formulario.reiniciar()
      setAviso(
        `Registraste la intervención en ${formatearDominio(registrada.dominio)} (${registrada.tipo}, ` +
          `${formatearMiles(registrada.kilometraje)} km). Se muestra como autorreportada.`,
      )
      setVehiculos(await listarVehiculos())
      window.scrollTo({ top: 0 })
    } catch (e) {
      const campos = e.campos ?? {}
      if (Object.keys(campos).length > 0) {
        formulario.mostrarErrores(campos)
        mostrarPrimerError()
      } else {
        setError(e.message)
      }
    } finally {
      setEnviando(false)
    }
  }

  return (
    <LayoutPanel enlaces={ENLACES_PROPIETARIO}>
      <h1 className="titulo-pagina">Registrar intervención propia</h1>
      <p className="subtitulo-pagina">
        Cargá un servicio que hiciste vos o que no registró un taller. Se va a mostrar como autorreportado.
      </p>

      {aviso && (
        <p className="aviso aviso-exito" role="status">
          <CircleCheck size={18} aria-hidden="true" />
          {aviso}
        </p>
      )}
      {error && (
        <p className="aviso aviso-error" role="alert">
          <CircleAlert size={18} aria-hidden="true" />
          {error}
        </p>
      )}

      {vehiculos?.length === 0 && (
        <div className="propia-sin-vehiculos">
          <p>Para registrar una intervención, primero vinculá un vehículo a tu cuenta.</p>
          <Link className="boton-secundario" to="/propietario">
            Ir a Mis vehículos
          </Link>
        </div>
      )}

      {vehiculo && (
        <div className="intervencion-grilla">
          <form className="tarjeta-intervencion" onSubmit={enviar} noValidate>
            <div className="propia-vehiculo">
              <SelectorVehiculo
                etiqueta="Vehículo"
                vehiculos={vehiculos}
                seleccionado={vehiculo.id}
                alSeleccionar={(id) => setParametros({ vehiculo: id }, { replace: true })}
              />
            </div>
            <CamposServicio formulario={formulario} ultimaLectura={vehiculo.ultima_lectura} />
            <ListaItems formulario={formulario} titulo="Insumos utilizados" />
            <CampoComprobante
              formulario={formulario}
              ayuda="Opcional. Si lo adjuntás, el registro lo indica en la consulta pública."
            />
            <CamposProximaRevision
              formulario={formulario}
              ayuda="Opcional. Te vamos a avisar cuando se acerque."
              conDetalle={false}
            />

            <p className="nota-movil">Una vez registrada, la intervención no se puede editar ni eliminar.</p>
            <div className="formulario-acciones">
              <Link className="boton-secundario" to="/propietario">
                Cancelar
              </Link>
              <button type="submit" className="boton-primario boton-ajustado" disabled={enviando}>
                <Check size={18} aria-hidden="true" />
                {enviando ? 'Registrando…' : 'Registrar intervención'}
              </button>
            </div>
          </form>

          <div className="propia-lateral">
            <VistaPrevia formulario={formulario} />
            <aside className="tarjeta-lateral">
              <h2>Tené en cuenta</h2>
              <ul>
                {TENE_EN_CUENTA.map((texto) => (
                  <li key={texto}>{texto}</li>
                ))}
              </ul>
            </aside>
          </div>
        </div>
      )}
    </LayoutPanel>
  )
}

export default IntervencionPropia
