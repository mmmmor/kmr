import { useEffect, useRef, useState } from 'react'
import { fechaEnArgentina, formatearFecha } from '../../utils/fechas.js'
import { formatearMiles } from '../../utils/intervenciones.js'

const ALTO = 200
const MARGEN = { arriba: 12, derecha: 16, abajo: 28, izquierda: 64 }
const SEPARACION_ETIQUETAS = 64 // px mínimos entre fechas del eje x

// "2026-04-02T03:00:00Z" → "04/2026" (Intl no respeta el mes de 2 dígitos sin el día).
function mesAnio(iso) {
  const [anio, mes] = fechaEnArgentina(iso).split('-')
  return `${mes}/${anio}`
}

// Paso "redondo" (1, 2 o 5 × 10ⁿ) para que el eje y tenga unas 3 o 4 divisiones.
function pasoRedondo(rango) {
  const crudo = Math.max(rango, 1) / 3
  const potencia = 10 ** Math.floor(Math.log10(crudo))
  const factor = [1, 2, 5, 10].find((f) => f * potencia >= crudo)
  return factor * potencia
}

function useAncho(referencia) {
  const [ancho, setAncho] = useState(0)
  useEffect(() => {
    const observador = new ResizeObserver(([entrada]) => setAncho(entrada.contentRect.width))
    observador.observe(referencia.current)
    return () => observador.disconnect()
  }, [referencia])
  return ancho
}

// Kilometraje de cada servicio a lo largo del tiempo (HU-013). Una sola serie: el título la nombra.
function GraficoKilometraje({ lecturas }) {
  const contenedor = useRef(null)
  const ancho = useAncho(contenedor)
  const [activo, setActivo] = useState(null)

  const kms = lecturas.map((l) => l.kilometraje)
  const paso = pasoRedondo(Math.max(...kms) - Math.min(...kms))
  const yMin = Math.floor(Math.min(...kms) / paso) * paso
  const yMax = Math.max(Math.ceil(Math.max(...kms) / paso) * paso, yMin + paso)
  const marcas = []
  for (let valor = yMin; valor <= yMax; valor += paso) marcas.push(valor)

  const tiempos = lecturas.map((l) => new Date(l.fecha).getTime())
  const t0 = Math.min(...tiempos)
  const rangoT = Math.max(...tiempos) - t0
  const plotAncho = Math.max(ancho - MARGEN.izquierda - MARGEN.derecha, 1)
  const plotAlto = ALTO - MARGEN.arriba - MARGEN.abajo
  // Si todos los servicios son del mismo día, se reparten parejo.
  const x = (i) =>
    MARGEN.izquierda + (rangoT > 0 ? ((tiempos[i] - t0) / rangoT) * plotAncho : (i / (lecturas.length - 1)) * plotAncho)
  const y = (km) => MARGEN.arriba + (1 - (km - yMin) / (yMax - yMin)) * plotAlto

  // Fechas del eje x sin pisarse: siempre la primera y la última, y las del medio si hay lugar.
  const conEtiqueta = new Set([0, lecturas.length - 1])
  let ultimaX = x(0)
  lecturas.forEach((_, i) => {
    if (i === 0 || i === lecturas.length - 1) return
    if (x(i) - ultimaX >= SEPARACION_ETIQUETAS && x(lecturas.length - 1) - x(i) >= SEPARACION_ETIQUETAS) {
      conEtiqueta.add(i)
      ultimaX = x(i)
    }
  })

  const primera = lecturas[0]
  const ultima = lecturas.at(-1)
  const resumen =
    `Kilometraje registrado: de ${formatearMiles(primera.kilometraje)} km el ${formatearFecha(primera.fecha)} ` +
    `a ${formatearMiles(ultima.kilometraje)} km el ${formatearFecha(ultima.fecha)}.`
  const puntos = lecturas.map((l, i) => `${x(i)},${y(l.kilometraje)}`).join(' ')

  return (
    <div className="grafico-km" ref={contenedor}>
      {ancho > 0 && (
        <svg width={ancho} height={ALTO} role="img" aria-label={resumen} onMouseLeave={() => setActivo(null)}>
          {marcas.map((valor) => (
            <g key={valor}>
              <line
                className="grafico-grilla"
                x1={MARGEN.izquierda}
                x2={ancho - MARGEN.derecha}
                y1={y(valor)}
                y2={y(valor)}
              />
              <text className="grafico-eje" x={MARGEN.izquierda - 10} y={y(valor)} dy="0.32em" textAnchor="end">
                {formatearMiles(valor)}
              </text>
            </g>
          ))}
          {[...conEtiqueta].map((i) => (
            <text
              key={i}
              className="grafico-eje"
              x={x(i)}
              y={ALTO - 8}
              textAnchor={i === 0 ? 'start' : i === lecturas.length - 1 ? 'end' : 'middle'}
            >
              {mesAnio(lecturas[i].fecha)}
            </text>
          ))}
          {activo !== null && (
            <line
              className="grafico-guia"
              x1={x(activo)}
              x2={x(activo)}
              y1={MARGEN.arriba}
              y2={ALTO - MARGEN.abajo}
            />
          )}
          <polyline className="grafico-linea" points={puntos} />
          {lecturas.map((l, i) => (
            <g key={i}>
              <circle
                className={`grafico-punto ${activo === i ? 'activo' : ''}`}
                cx={x(i)}
                cy={y(l.kilometraje)}
                r={activo === i ? 6 : 4.5}
              />
              {/* Zona de hover más grande que el punto. */}
              <circle
                className="grafico-zona"
                cx={x(i)}
                cy={y(l.kilometraje)}
                r={16}
                onMouseEnter={() => setActivo(i)}
              />
            </g>
          ))}
        </svg>
      )}
      {activo !== null && (
        <div
          className="grafico-tooltip"
          style={{
            left: Math.min(Math.max(x(activo), 70), ancho - 70),
            top: y(lecturas[activo].kilometraje) - 12,
          }}
        >
          <span>{formatearFecha(lecturas[activo].fecha)}</span>
          <strong className="mono">{formatearMiles(lecturas[activo].kilometraje)} km</strong>
          {lecturas[activo].valor_corregido && <span>Valor corregido</span>}
        </div>
      )}
      <table className="visualmente-oculto">
        <caption>Kilometraje registrado por fecha de servicio</caption>
        <thead>
          <tr>
            <th scope="col">Fecha</th>
            <th scope="col">Kilometraje</th>
          </tr>
        </thead>
        <tbody>
          {lecturas.map((l, i) => (
            <tr key={i}>
              <td>{formatearFecha(l.fecha)}</td>
              <td>
                {formatearMiles(l.kilometraje)} km{l.valor_corregido ? ' (valor corregido)' : ''}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default GraficoKilometraje
