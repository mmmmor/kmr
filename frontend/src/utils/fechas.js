// Las fechas llegan en UTC y se muestran en hora de Argentina.
const FORMATO_FECHA_HORA = new Intl.DateTimeFormat('es-AR', {
  timeZone: 'America/Argentina/Buenos_Aires',
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
  hour12: false,
})

// "2026-09-26T12:41:00Z" → "26/09/2026 09:41"
export function formatearFechaHora(iso) {
  return FORMATO_FECHA_HORA.format(new Date(iso)).replace(',', '')
}
