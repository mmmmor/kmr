import { formatearDominio, formatoDominio } from '../utils/dominio.js'
import './Patente.css'

// Dominio dibujado como placa: Mercosur (franja azul) o el modelo anterior (fondo negro).
// `tamano`: 'chico' (listas y selectores), 'mediano' (tarjetas) o 'grande' (vista previa).
function Patente({ dominio, tamano = 'mediano' }) {
  const texto = formatearDominio(dominio)
  const anterior = formatoDominio(dominio) === 'anterior'

  return (
    <span
      className={`patente patente-${anterior ? 'anterior' : 'mercosur'} patente-${tamano}`}
      role="img"
      aria-label={`Patente ${texto}`}
    >
      {anterior ? (
        <span className="patente-pais">ARGENTINA</span>
      ) : (
        <span className="patente-franja">
          REPÚBLICA ARGENTINA
          <span className="patente-bandera" />
        </span>
      )}
      <span className="patente-texto">{texto}</span>
    </span>
  )
}

export default Patente
