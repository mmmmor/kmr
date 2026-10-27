import { createContext, useContext } from 'react'

export const SesionContexto = createContext(null)

export function useSesion() {
  return useContext(SesionContexto)
}
