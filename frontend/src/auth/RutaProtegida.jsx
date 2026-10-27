import { Navigate, Outlet, useLocation } from 'react-router'
import { useSesion } from './contexto.js'
import { RUTA_POR_ROL } from './sesion.js'

// Sin sesión manda al login (y vuelve después); con otro rol, a su propia vista.
function RutaProtegida({ rol }) {
  const { sesion } = useSesion()
  const ubicacion = useLocation()

  if (!sesion) {
    return <Navigate to="/login" replace state={{ desde: ubicacion.pathname }} />
  }
  if (sesion.rol !== rol) {
    return <Navigate to={RUTA_POR_ROL[sesion.rol]} replace />
  }
  return <Outlet />
}

export default RutaProtegida
