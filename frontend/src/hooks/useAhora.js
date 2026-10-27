import { useEffect, useState } from 'react'

// Hora actual (en ms) que se actualiza cada `intervalo` ms, para cuentas regresivas.
export function useAhora(intervalo = 30000) {
  const [ahora, setAhora] = useState(() => Date.now())

  useEffect(() => {
    const id = setInterval(() => setAhora(Date.now()), intervalo)
    return () => clearInterval(id)
  }, [intervalo])

  return ahora
}
