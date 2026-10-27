export function soloDigitos(texto) {
  return texto.replace(/\D/g, '')
}

// "30715892347" → "30-71589234-7". Acepta cuits incompletos mientras se tipean.
export function formatearCuit(texto) {
  const d = soloDigitos(texto).slice(0, 11)
  if (d.length <= 2) return d
  if (d.length <= 10) return `${d.slice(0, 2)}-${d.slice(2)}`
  return `${d.slice(0, 2)}-${d.slice(2, 10)}-${d.slice(10)}`
}

// Posición del cursor en el texto formateado, después de `cantidad` dígitos.
export function posicionTrasDigitos(formateado, cantidad) {
  if (cantidad === 0) return 0
  let vistos = 0
  for (let i = 0; i < formateado.length; i++) {
    if (/\d/.test(formateado[i]) && ++vistos === cantidad) return i + 1
  }
  return formateado.length
}
