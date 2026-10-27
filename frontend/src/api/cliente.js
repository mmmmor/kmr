import { borrarSesion, leerSesion } from '../auth/sesion.js'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

// Error de la API con el mensaje listo para mostrar y, si hay, los errores por campo.
export class ErrorApi extends Error {
  constructor(mensaje, estado, campos = {}) {
    super(mensaje)
    this.estado = estado
    this.campos = campos
  }
}

// fetch con el token de la sesión. Con la sesión vencida o inválida, se vuelve al login.
async function solicitar(ruta, { method = 'GET', headers = {}, body } = {}) {
  const token = leerSesion()?.token
  if (token) headers.Authorization = `Bearer ${token}`

  let respuesta
  try {
    respuesta = await fetch(`${API_URL}${ruta}`, { method, headers, body })
  } catch {
    throw new ErrorApi('No pudimos conectarnos con el servidor. Probá de nuevo en unos minutos.', 0)
  }

  if (respuesta.status === 401 && token) {
    borrarSesion()
    window.location.assign('/login')
  }
  return respuesta
}

function errorDe(respuesta, datos) {
  return new ErrorApi(
    datos?.detail || 'Ocurrió un error inesperado. Probá de nuevo.',
    respuesta.status,
    datos?.campos,
  )
}

// `cuerpo` se envía como JSON; `formulario` (FormData) como multipart, para adjuntar archivos.
export async function pedir(ruta, { metodo = 'GET', cuerpo, formulario } = {}) {
  const headers = {}
  if (cuerpo) headers['Content-Type'] = 'application/json'
  const respuesta = await solicitar(ruta, {
    method: metodo,
    headers,
    body: formulario ?? (cuerpo ? JSON.stringify(cuerpo) : undefined),
  })

  const datos = await respuesta.json().catch(() => null)
  if (!respuesta.ok) throw errorDe(respuesta, datos)
  return datos
}

// Descarga un archivo protegido (por ejemplo, un comprobante) y lo devuelve como Blob.
export async function pedirArchivo(ruta) {
  const respuesta = await solicitar(ruta)
  if (!respuesta.ok) throw errorDe(respuesta, await respuesta.json().catch(() => null))
  return respuesta.blob()
}

export async function obtenerSalud() {
  const respuesta = await fetch(`${API_URL}/salud`)
  return respuesta.json()
}
