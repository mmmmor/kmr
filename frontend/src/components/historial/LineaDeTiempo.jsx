import { CalendarDays, FilePen, FileText, Link2, ShieldCheck, TriangleAlert, User } from 'lucide-react'
import { formatearFecha } from '../../utils/fechas.js'
import { formatearMiles, textoAlertaKilometraje, tituloCorreccion } from '../../utils/intervenciones.js'
import Badge from '../Badge.jsx'
import './LineaDeTiempo.css'

// "frenos y tren delantero a los 100.000 km o el 14/10/2026."
function textoProximaRevision({ detalle, kilometraje, fecha }) {
  const cuando = [
    kilometraje && `a los ${formatearMiles(kilometraje)} km`,
    fecha && `el ${formatearFecha(fecha)}`,
  ].filter(Boolean)
  const texto = [detalle, cuando.join(' o ')].filter(Boolean).join(' ')
  return `${texto}.`
}

function Items({ items }) {
  return (
    <ul className="linea-items">
      {items.map((item, i) => (
        <li key={i}>
          {item.descripcion} × {item.cantidad}
        </li>
      ))}
    </ul>
  )
}

function Registro({ intervencion, alVerComprobante, alCorregir }) {
  const { alerta_kilometraje: alerta, corrige_a: corrige, corregido_por: corregidoPor } = intervencion
  const esCorreccion = Boolean(corrige)
  const corregidos = new Set(intervencion.campos_corregidos)
  // En una corrección solo se repite lo que cambió; el kilometraje siempre se ve a la derecha.
  const mostrar = (campo) => !esCorreccion || corregidos.has(campo)
  const variante = esCorreccion ? 'correccion' : alerta ? 'alerta' : ''

  return (
    <li className={`linea-registro ${variante}`}>
      <span className="linea-punto" aria-hidden="true" />
      <article className="linea-tarjeta">
        <div className="linea-encabezado">
          <div>
            <p className="linea-fecha">{formatearFecha(intervencion.fecha)}</p>
            <h3>{esCorreccion ? tituloCorreccion(intervencion.campos_corregidos) : intervencion.tipo}</h3>
          </div>
          <p className={`linea-km mono ${alerta ? 'km-alerta' : ''}`}>{formatearMiles(intervencion.kilometraje)} km</p>
        </div>

        {esCorreccion && (
          <p className="linea-texto">
            <strong>Motivo:</strong> {intervencion.motivo_correccion}
          </p>
        )}
        {esCorreccion && corregidos.has('fecha_intervencion') && (
          <p className="linea-texto">
            <strong>Fecha del servicio:</strong> {formatearFecha(intervencion.fecha_intervencion)}
          </p>
        )}
        {esCorreccion && corregidos.has('tipo') && (
          <p className="linea-texto">
            <strong>Tipo de intervención:</strong> {intervencion.tipo}
          </p>
        )}
        {mostrar('descripcion') && intervencion.descripcion && (
          <p className="linea-texto linea-descripcion">{intervencion.descripcion}</p>
        )}
        {mostrar('items') && <Items items={intervencion.items} />}
        {mostrar('proxima_revision') && intervencion.proxima_revision && (
          <p className="linea-proxima">
            <CalendarDays size={16} aria-hidden="true" />
            <span>
              <strong>Próxima revisión:</strong> {textoProximaRevision(intervencion.proxima_revision)}
            </span>
          </p>
        )}

        <div className="linea-insignias">
          {intervencion.origen === 'taller' ? (
            <Badge tipo="exito" Icono={ShieldCheck}>
              Taller verificado · {intervencion.taller}
            </Badge>
          ) : (
            <Badge Icono={User}>Autorreportado por el propietario</Badge>
          )}
          {alerta && (
            <Badge tipo="ambar" Icono={TriangleAlert}>
              {textoAlertaKilometraje(alerta)}
            </Badge>
          )}
          {corrige && <Badge Icono={Link2}>Corrige el registro del {formatearFecha(corrige.fecha)}</Badge>}
          {corregidoPor && (
            <Badge Icono={Link2}>Corregido por el registro del {formatearFecha(corregidoPor.fecha)}</Badge>
          )}
          {intervencion.tiene_comprobante && <Badge Icono={FileText}>Con comprobante de insumos</Badge>}
          {intervencion.tiene_comprobante && alVerComprobante && (
            <button type="button" className="linea-accion" onClick={() => alVerComprobante(intervencion.id)}>
              <FileText size={14} aria-hidden="true" />
              Ver comprobante
            </button>
          )}
          {alCorregir && (
            <button type="button" className="linea-accion" onClick={() => alCorregir(intervencion)}>
              <FilePen size={14} aria-hidden="true" />
              Corregir
            </button>
          )}
        </div>
      </article>
    </li>
  )
}

// Historial de un vehículo, del más reciente al más antiguo (ya viene ordenado de la API).
// `alVerComprobante(id)`: solo para quien puede descargarlo (el propietario); la consulta pública no lo pasa.
// `puedeCorregir(intervencion)` y `alCorregir(intervencion)`: el botón "Corregir" de los registros que se pueden corregir.
function LineaDeTiempo({ intervenciones, alVerComprobante, puedeCorregir, alCorregir }) {
  return (
    <ol className="linea-tiempo">
      {intervenciones.map((intervencion) => (
        <Registro
          key={intervencion.id}
          intervencion={intervencion}
          alVerComprobante={alVerComprobante}
          alCorregir={puedeCorregir?.(intervencion) ? alCorregir : undefined}
        />
      ))}
    </ol>
  )
}

export default LineaDeTiempo
