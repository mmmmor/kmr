import { pedir } from './cliente.js'

export function listarVehiculos() {
  return pedir('/vehiculos')
}

export function vincularVehiculo({ dominio, marca, modelo, anio }) {
  return pedir('/vehiculos', { metodo: 'POST', cuerpo: { dominio, marca, modelo, anio } })
}

export function listarCodigos(vehiculoId) {
  return pedir(`/vehiculos/${vehiculoId}/codigos`)
}

export function generarCodigo(vehiculoId) {
  return pedir(`/vehiculos/${vehiculoId}/codigos`, { metodo: 'POST' })
}
