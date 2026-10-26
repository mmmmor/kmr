const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

export async function obtenerSalud() {
  const respuesta = await fetch(`${API_URL}/salud`)
  return respuesta.json()
}
