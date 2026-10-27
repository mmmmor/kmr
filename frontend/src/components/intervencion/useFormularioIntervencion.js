import { useState } from 'react'
import { hoyEnArgentina } from '../../utils/fechas.js'

const TAMANO_MAXIMO = 5 * 1024 * 1024
const TIPOS_COMPROBANTE = ['application/pdf', 'image/jpeg', 'image/png']

// Las claves de los datos y de los errores son las mismas que usa la API (por ejemplo,
// "proxima_revision.fecha" o "items.0.cantidad"), así sus errores se muestran tal cual.
function datosIniciales() {
  return {
    fecha_intervencion: hoyEnArgentina(),
    kilometraje: '',
    tipo: '',
    descripcion: '',
    'proxima_revision.kilometraje': '',
    'proxima_revision.fecha': '',
    'proxima_revision.detalle': '',
  }
}

function itemVacio() {
  return { clave: crypto.randomUUID(), descripcion: '', cantidad: '1' }
}

// Lleva a la vista el primer campo con error (y lo enfoca si se puede escribir en él).
export function mostrarPrimerError() {
  requestAnimationFrame(() => {
    const primero = document.querySelector('[aria-invalid="true"], .seccion-intervencion [role="alert"]')
    primero?.scrollIntoView({ block: 'center' })
    if (primero?.matches('input, select, textarea')) primero.focus({ preventScroll: true })
  })
}

function sinErrores(errores, prefijos) {
  return Object.fromEntries(
    Object.entries(errores).filter(([clave]) => !prefijos.some((p) => clave === p || clave.startsWith(`${p}.`))),
  )
}

// Estado, validación y armado del pedido del formulario de intervención (taller y propietario).
export function useFormularioIntervencion() {
  const [datos, setDatos] = useState(datosIniciales)
  const [items, setItems] = useState(() => [itemVacio()])
  const [comprobante, setComprobante] = useState(null)
  const [errores, setErrores] = useState({})

  function cambiar(campo, valor) {
    setDatos((anteriores) => ({ ...anteriores, [campo]: valor }))
    const proxima = campo.startsWith('proxima_revision.')
    setErrores((anteriores) => {
      const sinEste = sinErrores(anteriores, [campo])
      return proxima ? sinErrores(sinEste, ['proxima_revision']) : sinEste
    })
  }

  function cambiarItem(clave, campo, valor) {
    setItems((anteriores) => anteriores.map((item) => (item.clave === clave ? { ...item, [campo]: valor } : item)))
    setErrores((anteriores) => sinErrores(anteriores, ['items']))
  }

  function agregarItem() {
    setItems((anteriores) => [...anteriores, itemVacio()])
    setErrores((anteriores) => sinErrores(anteriores, ['items']))
  }

  function quitarItem(clave) {
    setItems((anteriores) => anteriores.filter((item) => item.clave !== clave))
    setErrores((anteriores) => sinErrores(anteriores, ['items']))
  }

  // Control previo del archivo; el backend igual verifica su contenido real.
  function elegirComprobante(archivo) {
    setErrores((anteriores) => sinErrores(anteriores, ['comprobante']))
    if (archivo && !TIPOS_COMPROBANTE.includes(archivo.type)) {
      setErrores((anteriores) => ({
        ...anteriores,
        comprobante: 'El comprobante tiene que ser un archivo PDF, JPG o PNG.',
      }))
      return
    }
    if (archivo && archivo.size > TAMANO_MAXIMO) {
      setErrores((anteriores) => ({ ...anteriores, comprobante: 'El comprobante no puede superar los 5 MB.' }))
      return
    }
    setComprobante(archivo)
  }

  // Marca los campos obligatorios vacíos sin llamar a la API. Devuelve true si se puede enviar.
  function validar() {
    const nuevos = {}
    if (!datos.fecha_intervencion) nuevos.fecha_intervencion = 'Completá este campo.'
    else if (datos.fecha_intervencion > hoyEnArgentina()) {
      nuevos.fecha_intervencion = 'La fecha no puede ser posterior a hoy.'
    }
    if (datos.kilometraje === '') nuevos.kilometraje = 'Completá este campo.'
    if (!datos.tipo) nuevos.tipo = 'Completá este campo.'
    if (items.length === 0) nuevos.items = 'Agregá al menos un ítem.'
    items.forEach((item, i) => {
      if (!item.descripcion.trim()) nuevos[`items.${i}.descripcion`] = 'Completá este campo.'
      if (!item.cantidad) nuevos[`items.${i}.cantidad`] = 'Completá este campo.'
      else if (Number(item.cantidad) < 1) nuevos[`items.${i}.cantidad`] = 'Ingresá una cantidad entre 1 y 9.999.'
    })
    const proximaKm = datos['proxima_revision.kilometraje']
    const proximaFecha = datos['proxima_revision.fecha']
    if (datos['proxima_revision.detalle'].trim() && !proximaKm && !proximaFecha) {
      nuevos.proxima_revision = 'Indicá el kilometraje o la fecha de la próxima revisión.'
    }
    setErrores((anteriores) => ({ ...(anteriores.comprobante && { comprobante: anteriores.comprobante }), ...nuevos }))
    return Object.keys(nuevos).length === 0
  }

  // Cuerpo para la API (sin el comprobante, que va aparte).
  function aEntrada() {
    const proximaKm = datos['proxima_revision.kilometraje']
    const proximaFecha = datos['proxima_revision.fecha']
    const proximaDetalle = datos['proxima_revision.detalle'].trim()
    return {
      fecha_intervencion: datos.fecha_intervencion,
      kilometraje: Number(datos.kilometraje),
      tipo: datos.tipo,
      descripcion: datos.descripcion.trim() || null,
      items: items.map(({ descripcion, cantidad }) => ({ descripcion: descripcion.trim(), cantidad: Number(cantidad) })),
      proxima_revision:
        proximaKm || proximaFecha || proximaDetalle
          ? {
              kilometraje: proximaKm ? Number(proximaKm) : null,
              fecha: proximaFecha || null,
              detalle: proximaDetalle || null,
            }
          : null,
    }
  }

  function reiniciar() {
    setDatos(datosIniciales())
    setItems([itemVacio()])
    setComprobante(null)
    setErrores({})
  }

  return {
    datos,
    items,
    comprobante,
    errores,
    cambiar,
    cambiarItem,
    agregarItem,
    quitarItem,
    elegirComprobante,
    validar,
    aEntrada,
    reiniciar,
    mostrarErrores: setErrores,
  }
}
