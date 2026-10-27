import { pedir } from './cliente.js'

export function listarSolicitudes(estado) {
  return pedir(`/admin/solicitudes?estado=${estado}`)
}

export function aprobarSolicitud(id) {
  return pedir(`/admin/solicitudes/${id}/aprobar`, { metodo: 'POST' })
}

export function rechazarSolicitud(id, motivo) {
  return pedir(`/admin/solicitudes/${id}/rechazar`, { metodo: 'POST', cuerpo: { motivo } })
}
