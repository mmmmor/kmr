const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

// Error de la API con el mensaje listo para mostrar y, si hay, los errores por campo.
export class ErrorApi extends Error {
  constructor(mensaje, estado, campos = {}) {
    super(mensaje)
    this.estado = estado
    this.campos = campos
  }
}

export async function pedir(ruta, { metodo = 'GET', cuerpo } = {}) {
  let respuesta
  try {
    respuesta = await fetch(`${API_URL}${ruta}`, {
      method: metodo,
      headers: cuerpo ? { 'Content-Type': 'application/json' } : undefined,
      body: cuerpo ? JSON.stringify(cuerpo) : undefined,
    })
  } catch {
    throw new ErrorApi('No pudimos conectarnos con el servidor. Probá de nuevo en unos minutos.', 0)
  }

  const datos = await respuesta.json().catch(() => null)
  if (!respuesta.ok) {
    throw new ErrorApi(
      datos?.detail || 'Ocurrió un error inesperado. Probá de nuevo.',
      respuesta.status,
      datos?.campos,
    )
  }
  return datos
}

export async function obtenerSalud() {
  const respuesta = await fetch(`${API_URL}/salud`)
  return respuesta.json()
}
