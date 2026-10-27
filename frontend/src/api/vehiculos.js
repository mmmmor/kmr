import { pedir } from './cliente.js'

export function listarVehiculos() {
  return pedir('/vehiculos')
}

export function vincularVehiculo({ dominio, marca, modelo, anio }) {
  return pedir('/vehiculos', { metodo: 'POST', cuerpo: { dominio, marca, modelo, anio } })
}
