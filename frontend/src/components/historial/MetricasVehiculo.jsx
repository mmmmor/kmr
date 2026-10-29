import { formatearFecha } from '../../utils/fechas.js'
import { formatearMiles } from '../../utils/intervenciones.js'
import GraficoKilometraje from './GraficoKilometraje.jsx'
import './MetricasVehiculo.css'

function Dato({ titulo, valor, unidad, detalle }) {
  return (
    <div className="metrica">
      <dt>{titulo}</dt>
      <dd>
        <span className="metrica-valor mono">
          {valor ?? '—'}
          {valor !== null && valor !== undefined && unidad && ` ${unidad}`}
        </span>
        {detalle && <span className="metrica-detalle">{detalle}</span>}
      </dd>
    </div>
  )
}

function Barras({ titulo, filas, total }) {
  return (
    <div className="metricas-barras">
      <h4>{titulo}</h4>
      <ul>
        {filas.map(({ nombre, cantidad, secundaria }) => (
          <li key={nombre}>
            <span className="metricas-barra-nombre">{nombre}</span>
            <span className="metricas-barra-cantidad mono">{cantidad}</span>
            <span className="metricas-barra-pista" aria-hidden="true">
              <span
                className={`metricas-barra ${secundaria ? 'secundaria' : ''}`}
                style={{ width: `${(cantidad / total) * 100}%` }}
              />
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}

// Métricas de mantenimiento del historial del propietario (HU-013).
function MetricasVehiculo({ metricas }) {
  const { servicios, correcciones, lecturas } = metricas
  const corregidas = lecturas.filter((l) => l.valor_corregido)
  // Con 2 servicios o más, un promedio en km sin calcular quiere decir que el último km es menor al primero.
  const kmNoCrece = servicios >= 2 && metricas.frecuencia_km === null
  const maximoPorTipo = Math.max(...metricas.por_tipo.map((t) => t.cantidad))
  const origenes = [
    { nombre: 'Taller verificado', cantidad: metricas.por_taller },
    { nombre: 'Autorreportado', cantidad: metricas.autorreportados, secundaria: true },
  ].filter((o) => o.cantidad > 0)

  return (
    <section className="metricas" aria-labelledby="titulo-metricas">
      <h2 id="titulo-metricas">Métricas de mantenimiento</h2>
      <p className="metricas-bajada">Calculadas a partir de los registros del vehículo.</p>

      <dl className="metricas-datos">
        <Dato
          titulo="Servicios registrados"
          valor={servicios}
          detalle={correcciones > 0 && `Más ${correcciones} ${correcciones === 1 ? 'corrección' : 'correcciones'}`}
        />
        <Dato
          titulo="Promedio entre servicios"
          valor={formatearMiles(metricas.frecuencia_km) || null}
          unidad="km"
          detalle={kmNoCrece && 'El kilometraje registrado no es creciente.'}
        />
        <Dato titulo="Frecuencia promedio" valor={metricas.frecuencia_dias} unidad="días" />
        <Dato
          titulo="Uso estimado"
          valor={formatearMiles(metricas.uso_km_mes) || null}
          unidad="km/mes"
          detalle={kmNoCrece && 'El kilometraje registrado no es creciente.'}
        />
      </dl>
      {servicios < 2 && (
        <p className="metricas-nota">
          Con un solo servicio registrado todavía no se puede calcular la frecuencia de mantenimiento: se calcula a
          partir del segundo.
        </p>
      )}

      <div className="metricas-graficos">
        {lecturas.length >= 2 && (
          <div className="metricas-tarjeta">
            <h3>Kilometraje registrado</h3>
            <GraficoKilometraje lecturas={lecturas} />
            {corregidas.map((l) => (
              <p key={l.fecha} className="metricas-nota">
                Para el registro del {formatearFecha(l.fecha)} se usa el valor corregido (
                {formatearMiles(l.kilometraje)} km).
              </p>
            ))}
          </div>
        )}
        <div className="metricas-tarjeta">
          <Barras
            titulo="Tipos de intervención"
            filas={metricas.por_tipo.map((t) => ({ nombre: t.tipo, cantidad: t.cantidad }))}
            total={maximoPorTipo}
          />
          <Barras titulo="Origen de los registros" filas={origenes} total={servicios} />
        </div>
      </div>
    </section>
  )
}

export default MetricasVehiculo
