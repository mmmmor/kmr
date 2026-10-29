import { pedir } from './cliente.js'

// Historial público de un vehículo (HU-010). No necesita sesión.
export function consultarDominio(dominio) {
  return pedir(`/publico/vehiculos/${encodeURIComponent(dominio)}`)
}
