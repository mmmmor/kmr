import { pedir } from './cliente.js'

export function solicitarAltaTaller(datos) {
  const { nombre, apellido, correo, contrasena, razon_social, cuit, domicilio, telefono } = datos
  return pedir('/talleres/solicitud', {
    metodo: 'POST',
    cuerpo: { nombre, apellido, correo, contrasena, razon_social, cuit, domicilio, telefono },
  })
}
