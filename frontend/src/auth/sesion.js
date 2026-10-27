// Sesión guardada en sessionStorage: se borra al cerrar la pestaña o al cerrar sesión.
const CLAVE = 'kmr_sesion'

export const RUTA_POR_ROL = {
  propietario: '/propietario',
  taller: '/taller',
  administrador: '/admin',
}

export function leerSesion() {
  try {
    const sesion = JSON.parse(sessionStorage.getItem(CLAVE))
    if (!sesion?.token || tokenVencido(sesion.token)) {
      borrarSesion()
      return null
    }
    return sesion
  } catch {
    return null
  }
}

export function guardarSesion(sesion) {
  try {
    sessionStorage.setItem(CLAVE, JSON.stringify(sesion))
  } catch {
    // Sin sessionStorage (modo privado estricto) la sesión vive solo en memoria.
  }
}

export function borrarSesion() {
  try {
    sessionStorage.removeItem(CLAVE)
  } catch {
    // Nada que borrar.
  }
}

// Lee el vencimiento del JWT. No valida la firma: eso lo hace siempre el backend.
function tokenVencido(token) {
  try {
    const base64 = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')
    const { exp } = JSON.parse(atob(base64))
    return !exp || exp * 1000 <= Date.now()
  } catch {
    return true
  }
}
