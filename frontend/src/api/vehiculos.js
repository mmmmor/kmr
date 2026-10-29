import { pedir } from './cliente.js'

export function listarVehiculos() {
  return pedir('/vehiculos')
}

export function vincularVehiculo({ dominio, marca, modelo, anio }) {
  return pedir('/vehiculos', { metodo: 'POST', cuerpo: { dominio, marca, modelo, anio } })
}

// Historial completo del vehículo, con correcciones e integridad de la cadena (HU-012).
export function obtenerHistorial(vehiculoId) {
  return pedir(`/vehiculos/${vehiculoId}/historial`)
}

export function listarCodigos(vehiculoId) {
  return pedir(`/vehiculos/${vehiculoId}/codigos`)
}

export function generarCodigo(vehiculoId) {
  return pedir(`/vehiculos/${vehiculoId}/codigos`, { metodo: 'POST' })
}

// Intervención autorreportada. `comprobante`: File opcional.
export function registrarIntervencionPropia(vehiculoId, datos, comprobante) {
  const formulario = new FormData()
  formulario.append('datos', JSON.stringify(datos))
  if (comprobante) formulario.append('comprobante', comprobante)
  return pedir(`/vehiculos/${vehiculoId}/intervenciones`, { metodo: 'POST', formulario })
}
