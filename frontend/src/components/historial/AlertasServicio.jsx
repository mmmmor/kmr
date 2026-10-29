import { Bell, BellRing } from 'lucide-react'
import { formatearFecha } from '../../utils/fechas.js'
import { formatearMiles } from '../../utils/intervenciones.js'
import './AlertasServicio.css'

function dias(cantidad) {
  return cantidad === 1 ? '1 día' : `${cantidad} días`
}

// "Recomendada por Lubricentro San Martín a los 100.000 km o el 14/10/2026."
function textoRecomendacion(alerta) {
  const cuando = [
    alerta.kilometraje !== null && `a los ${formatearMiles(alerta.kilometraje)} km`,
    alerta.fecha && `el ${formatearFecha(alerta.fecha)}`,
  ]
    .filter(Boolean)
    .join(' o ')
  const quien = alerta.taller ? `Recomendada por ${alerta.taller}` : 'La registraste vos'
  return `${quien} en el servicio del ${formatearFecha(alerta.fecha_servicio)}, ${cuando}.`
}

// "Faltan 1.550 km o 18 días." / "Superaste el kilometraje por 450 km y la fecha pasó hace 3 días."
function textoRestante({ estado, km_restantes: km, dias_restantes: d }) {
  if (estado === 'vencido') {
    const partes = [
      km !== null && km < 0 && `superaste el kilometraje por ${formatearMiles(-km)} km`,
      d !== null && d < 0 && `la fecha pasó hace ${dias(-d)}`,
    ].filter(Boolean)
    const texto = partes.join(' y ')
    return `${texto[0].toUpperCase()}${texto.slice(1)}.`
  }
  const partes = [km !== null && `${formatearMiles(km)} km`, d !== null && dias(d)].filter(Boolean)
  return `Faltan ${partes.join(' o ')}.`
}

// Avisos de próxima revisión cercana o vencida en el historial del propietario (HU-014).
function AlertasServicio({ alertas }) {
  return (
    <div className="alertas-servicio">
      {alertas.map((alerta) => {
        const vencida = alerta.estado === 'vencido'
        const Icono = vencida ? BellRing : Bell
        return (
          <div
            key={alerta.intervencion_id}
            className={`alerta-servicio ${vencida ? 'vencida' : ''}`}
            role={vencida ? 'alert' : 'status'}
          >
            <Icono size={20} aria-hidden="true" />
            <div>
              <p className="alerta-servicio-titulo">
                {vencida ? 'Revisión vencida' : 'Revisión próxima'}: {alerta.detalle ?? alerta.tipo}
              </p>
              <p>
                {textoRecomendacion(alerta)} {textoRestante(alerta)}
              </p>
            </div>
            <a href={`#registro-${alerta.intervencion_id}`}>Ver servicio</a>
          </div>
        )
      })}
    </div>
  )
}

export default AlertasServicio
