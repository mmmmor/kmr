import { pedirArchivo } from './cliente.js'

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
