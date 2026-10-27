import { soloDigitos } from '../utils/cuit.js'
import { pedir } from './cliente.js'

export function solicitarAltaTaller(datos) {
  const { nombre, apellido, correo, contrasena, razon_social, cuit, domicilio, telefono } = datos
  return pedir('/talleres/solicitud', {
    metodo: 'POST',
    // El campo muestra el CUIT con guiones; a la API se envían solo los 11 dígitos.
    cuerpo: { nombre, apellido, correo, contrasena, razon_social, cuit: soloDigitos(cuit), domicilio, telefono },
  })
}
