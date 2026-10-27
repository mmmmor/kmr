import { useState } from 'react'
import { Check, CircleAlert, ShieldCheck } from 'lucide-react'
import { registrarIntervencion } from '../../api/taller.js'
import Badge from '../../components/Badge.jsx'
import {
  CampoComprobante,
  CamposProximaRevision,
  CamposServicio,
  ListaItems,
} from '../../components/intervencion/SeccionesIntervencion.jsx'
import Patente from '../../components/Patente.jsx'
import { mostrarPrimerError } from '../../components/intervencion/useFormularioIntervencion.js'
import { formatearFecha } from '../../utils/fechas.js'
import { formatearMiles } from '../../utils/intervenciones.js'

const ANTES_DE_REGISTRAR = [
  'El registro no se puede editar ni eliminar.',
  'Al registrar, el código del propietario se consume: para otra intervención va a necesitar uno nuevo.',
]

// Paso 2: datos del servicio. `formulario` viene de la pantalla, así los datos no se pierden
// si hay que volver al paso 1 a ingresar otro código.
function PasoDatos({ autorizacion, formulario, alRegistrar, alCancelar, alRechazarCodigo }) {
  const { vehiculo, codigo } = autorizacion
  const [enviando, setEnviando] = useState(false)
  const [errorGeneral, setErrorGeneral] = useState('')
  const ultima = vehiculo.ultima_lectura

  async function enviar(evento) {
    evento.preventDefault()
    setErrorGeneral('')
    if (!formulario.validar()) {
      mostrarPrimerError()
      return
    }

    setEnviando(true)
    try {
      const datos = { dominio: vehiculo.dominio, codigo, ...formulario.aEntrada() }
      alRegistrar(await registrarIntervencion(datos, formulario.comprobante))
    } catch (error) {
      setEnviando(false)
      const campos = error.campos ?? {}
      if (campos.codigo) {
        alRechazarCodigo(campos.codigo)
      } else if (Object.keys(campos).length > 0) {
        formulario.mostrarErrores(campos)
        mostrarPrimerError()
      } else {
        setErrorGeneral(error.message)
      }
    }
  }

  return (
    <>
      <div className="vehiculo-autorizado">
        <Patente dominio={vehiculo.dominio} />
        <div className="vehiculo-autorizado-datos">
          <strong>
            {vehiculo.marca} {vehiculo.modelo} · Modelo {vehiculo.anio}
          </strong>
          <span>
            {ultima ? (
              <>
                Último kilometraje registrado: <span className="mono">{formatearMiles(ultima.kilometraje)} km</span>{' '}
                el {formatearFecha(ultima.fecha)}
              </>
            ) : (
              'Todavía no tiene kilometrajes registrados.'
            )}
          </span>
        </div>
        <div className="vehiculo-autorizado-acciones">
          <Badge tipo="exito" Icono={ShieldCheck}>
            Autorizado por el propietario · código {codigo.slice(0, 3)} {codigo.slice(3)}
          </Badge>
          <button type="button" className="boton-texto" onClick={alCancelar}>
            Cambiar vehículo
          </button>
        </div>
      </div>

      <div className="taller-grilla">
        <form className="tarjeta-taller" onSubmit={enviar} noValidate>
          {errorGeneral && (
            <p className="aviso aviso-error" role="alert">
              <CircleAlert size={18} aria-hidden="true" />
              {errorGeneral}
            </p>
          )}
          <CamposServicio formulario={formulario} ultimaLectura={ultima} />
          <ListaItems formulario={formulario} titulo="Insumos y trabajos" />
          <CamposProximaRevision
            formulario={formulario}
            ayuda="Opcional. El propietario recibe una alerta cuando se acerca."
          />
          <CampoComprobante formulario={formulario} ayuda="Opcional. Factura o remito del servicio." />

          <p className="nota-movil">
            El registro no se puede editar ni eliminar. Al registrar, el código del propietario se consume.
          </p>
          <div className="formulario-acciones">
            <button type="button" className="boton-secundario" onClick={alCancelar}>
              Cancelar
            </button>
            <button type="submit" className="boton-primario boton-ajustado" disabled={enviando}>
              <Check size={18} aria-hidden="true" />
              {enviando ? 'Registrando…' : 'Registrar intervención'}
            </button>
          </div>
        </form>

        <aside className="antes-de-registrar">
          <h2>Antes de registrar</h2>
          <ul>
            {ANTES_DE_REGISTRAR.map((texto) => (
              <li key={texto}>{texto}</li>
            ))}
          </ul>
        </aside>
      </div>
    </>
  )
}

export default PasoDatos
