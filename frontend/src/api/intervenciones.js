import { pedir, pedirArchivo } from './cliente.js'

// Corrección vinculada (HU-011): `datos` son los del registro ya corregidos, más el `motivo`.
export function corregirIntervencion(intervencionId, datos) {
  return pedir(`/intervenciones/${intervencionId}/correcciones`, { metodo: 'POST', cuerpo: datos })
}

// Abre el comprobante en otra pestaña. La pestaña se abre antes de la descarga (en el mismo clic)
// para que el navegador no la bloquee; el archivo necesita el token, por eso no alcanza con un enlace.
export async function abrirComprobante(intervencionId) {
  const pestana = window.open('', '_blank')
  try {
    const archivo = await pedirArchivo(`/intervenciones/${intervencionId}/comprobante`)
    pestana.location.href = URL.createObjectURL(archivo)
  } catch (error) {
    pestana?.close()
    throw error
  }
}
