import { pedir } from './cliente.js'

export function autorizar({ dominio, codigo }) {
  return pedir('/taller/autorizacion', { metodo: 'POST', cuerpo: { dominio, codigo } })
}

// `datos`: dominio, código y datos del servicio. `comprobante`: File opcional.
export function registrarIntervencion(datos, comprobante) {
  const formulario = new FormData()
  formulario.append('datos', JSON.stringify(datos))
  if (comprobante) formulario.append('comprobante', comprobante)
  return pedir('/taller/intervenciones', { metodo: 'POST', formulario })
}

export function listarRegistros() {
  return pedir('/taller/intervenciones')
}
