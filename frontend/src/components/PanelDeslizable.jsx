import { useEffect, useRef } from 'react'
import { X } from 'lucide-react'
import './PanelDeslizable.css'

// Panel que entra desde la derecha (pantalla completa en el celular). Usa <dialog> modal:
// el navegador encierra el foco, cierra con Escape y oscurece el fondo.
function PanelDeslizable({ abierto, titulo, alCerrar, children }) {
  const dialogo = useRef(null)
  const presionoElFondo = useRef(false)

  useEffect(() => {
    const elemento = dialogo.current
    if (abierto && !elemento.open) elemento.showModal()
    if (!abierto && elemento.open) elemento.close()
  }, [abierto])

  return (
    <dialog
      ref={dialogo}
      className="deslizable"
      aria-labelledby="deslizable-titulo"
      onClose={alCerrar}
      // Un clic en el fondo oscuro llega al <dialog> mismo y cierra el panel. Se exige que también
      // el botón se haya presionado ahí, para no cerrarlo al arrastrar una selección de texto.
      onMouseDown={(evento) => (presionoElFondo.current = evento.target === dialogo.current)}
      onClick={(evento) => presionoElFondo.current && evento.target === dialogo.current && alCerrar()}
    >
      {abierto && (
        <div className="deslizable-contenido">
          <header className="deslizable-encabezado">
            <h2 id="deslizable-titulo">{titulo}</h2>
            <button type="button" className="deslizable-cerrar" aria-label="Cerrar" onClick={alCerrar}>
              <X size={24} aria-hidden="true" />
            </button>
          </header>
          {children}
        </div>
      )}
    </dialog>
  )
}

export default PanelDeslizable
