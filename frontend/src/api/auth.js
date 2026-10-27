import { pedir } from './cliente.js'

export function registrarPropietario({ nombre, apellido, correo, contrasena }) {
  return pedir('/auth/registro', {
    metodo: 'POST',
    cuerpo: { nombre, apellido, correo, contrasena },
  })
}
