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

// Recuperación de contraseña (HU-015): la respuesta es la misma exista o no la cuenta.
export function recuperarContrasena(correo) {
  return pedir('/auth/recuperar', { metodo: 'POST', cuerpo: { correo } })
}

export function restablecerContrasena(token, contrasena) {
  return pedir('/auth/restablecer', { metodo: 'POST', cuerpo: { token, contrasena } })
}
