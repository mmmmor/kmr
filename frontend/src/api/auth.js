import { pedir } from './cliente.js'

export function iniciarSesion({ correo, contrasena }) {
  return pedir('/auth/login', { metodo: 'POST', cuerpo: { correo, contrasena } })
}

export function registrarPropietario({ nombre, apellido, correo, contrasena }) {
  return pedir('/auth/registro', {
    metodo: 'POST',
    cuerpo: { nombre, apellido, correo, contrasena },
  })
}
