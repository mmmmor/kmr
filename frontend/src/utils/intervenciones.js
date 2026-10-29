import { formatearFecha } from './fechas.js'

// Misma lista que backend/app/modelos/intervencion.py: el backend rechaza cualquier otro tipo.
export const TIPOS_INTERVENCION = [
  'Cambio de aceite y filtros',
  'Frenos',
  'Suspensión y tren delantero',
  'Neumáticos, alineación y balanceo',
  'Distribución',
  'Embrague y transmisión',
  'Batería y sistema eléctrico',
  'Refrigeración',
  'Encendido e inyección',
  'Aire acondicionado',
  'Escape',
  'Revisión general',
  'Otro',
]

const MILES = new Intl.NumberFormat('es-AR')

// Alerta de kilometraje de una intervención (HU-009), con la lectura contra la que se comparó.
export function textoAlertaKilometraje(alerta) {
  const anterior = `${formatearMiles(alerta.kilometraje_anterior)} km`
  if (alerta.tipo === 'kilometraje_inferior') return `Kilometraje inferior al último registrado (${anterior})`
  return `Incremento incompatible con el tiempo transcurrido (${anterior} el ${formatearFecha(alerta.fecha_anterior)})`
}

// 100210 o "100210" → "100.210"
export function formatearMiles(valor) {
  if (valor === '' || valor === null || valor === undefined) return ''
  return MILES.format(Number(valor))
}

// 184320 → "180 KB"; 2400000 → "2,3 MB"
export function formatearTamano(bytes) {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`
  return `${(bytes / (1024 * 1024)).toLocaleString('es-AR', { maximumFractionDigits: 1 })} MB`
}
