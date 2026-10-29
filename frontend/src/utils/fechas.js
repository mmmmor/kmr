// Las fechas llegan en UTC y se muestran en hora de Argentina.
const ZONA = 'America/Argentina/Buenos_Aires'
const FECHA = { day: '2-digit', month: '2-digit', year: 'numeric' }
const HORA = { hour: '2-digit', minute: '2-digit', hour12: false }

const FORMATO_FECHA_HORA = new Intl.DateTimeFormat('es-AR', { timeZone: ZONA, ...FECHA, ...HORA })
const FORMATO_FECHA = new Intl.DateTimeFormat('es-AR', { timeZone: ZONA, ...FECHA })
const FORMATO_HORA = new Intl.DateTimeFormat('es-AR', { timeZone: ZONA, ...HORA })

// "2026-09-26T12:41:00Z" → "26/09/2026 09:41"
export function formatearFechaHora(iso) {
  return FORMATO_FECHA_HORA.format(new Date(iso)).replace(',', '')
}

// "2026-09-26T12:41:00Z" → "26/09/2026"
export function formatearFecha(iso) {
  return FORMATO_FECHA.format(new Date(iso))
}

// "2026-09-26T12:41:00Z" → "09:41"
export function formatearHora(iso) {
  return FORMATO_HORA.format(new Date(iso))
}

const FORMATO_ISO = new Intl.DateTimeFormat('en-CA', { timeZone: ZONA })

// Fecha de hoy en Argentina como "aaaa-mm-dd" (el formato de <input type="date">).
export function hoyEnArgentina() {
  return FORMATO_ISO.format(new Date())
}

// "2026-06-18T03:00:00Z" → "2026-06-18": el día en Argentina, para un <input type="date"> o la API.
export function fechaEnArgentina(iso) {
  return FORMATO_ISO.format(new Date(iso))
}

// Tiempo que falta hasta `iso`: "23 h 41 min", "41 min" o "menos de 1 min".
export function tiempoRestante(iso, ahora = Date.now()) {
  const minutos = Math.floor((new Date(iso) - ahora) / 60000)
  if (minutos < 1) return 'menos de 1 min'
  const horas = Math.floor(minutos / 60)
  return horas > 0 ? `${horas} h ${minutos % 60} min` : `${minutos} min`
}
