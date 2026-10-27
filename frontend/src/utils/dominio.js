const MERCOSUR = /^[A-Z]{2}\d{3}[A-Z]{2}$/
const ANTERIOR = /^[A-Z]{3}\d{3}$/

// Igual que el backend: mayúsculas, sin espacios ni guiones. " ae-123 cd " → "AE123CD"
export function normalizarDominio(texto) {
  return texto.replace(/[\s-]/g, '').toUpperCase()
}

// 'mercosur' (AA111AA), 'anterior' (AAA111) o null si todavía no es un dominio válido.
export function formatoDominio(dominio) {
  if (MERCOSUR.test(dominio)) return 'mercosur'
  if (ANTERIOR.test(dominio)) return 'anterior'
  return null
}

// Formato de placa: "AE123CD" → "AE 123 CD", "NTR215" → "NTR 215".
export function formatearDominio(dominio) {
  const formato = formatoDominio(dominio)
  if (formato === 'mercosur') return `${dominio.slice(0, 2)} ${dominio.slice(2, 5)} ${dominio.slice(5)}`
  if (formato === 'anterior') return `${dominio.slice(0, 3)} ${dominio.slice(3)}`
  return dominio
}
