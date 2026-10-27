import { useCallback, useMemo, useState } from 'react'
import { SesionContexto } from './contexto.js'
import { borrarSesion, guardarSesion, leerSesion } from './sesion.js'

function SesionProvider({ children }) {
  const [sesion, setSesion] = useState(leerSesion)

  const iniciar = useCallback((nueva) => {
    guardarSesion(nueva)
    setSesion(nueva)
  }, [])

  const cerrar = useCallback(() => {
    borrarSesion()
    setSesion(null)
  }, [])

  const valor = useMemo(() => ({ sesion, iniciar, cerrar }), [sesion, iniciar, cerrar])

  return <SesionContexto.Provider value={valor}>{children}</SesionContexto.Provider>
}

export default SesionProvider
