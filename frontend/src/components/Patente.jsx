import { formatearDominio, formatoDominio } from '../utils/dominio.js'
import './Patente.css'

// Escudo nacional simplificado para la placa del modelo anterior: sol, óvalo celeste y blanco, y laureles.
function Escudo() {
  return (
    <svg className="patente-escudo" viewBox="0 0 20 24" aria-hidden="true">
      <circle cx="10" cy="4" r="3" fill="#f6b40e" />
      <path d="M3.6 14.5a6.4 7.5 0 0 1 12.8 0z" fill="#74acdf" />
      <path d="M3.6 14.5a6.4 7.5 0 0 0 12.8 0z" fill="#fff" />
      <ellipse cx="10" cy="14.5" rx="6.4" ry="7.5" fill="none" stroke="#5b6066" strokeWidth="0.9" />
      <path d="M3 9.5q-2 5 1.5 11M17 9.5q2 5-1.5 11" fill="none" stroke="#3f8f4a" strokeWidth="1.6" />
    </svg>
  )
}

// Dominio dibujado como placa: Mercosur (franja azul) o el modelo anterior (chapa clara con el panel negro).
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
        <span className="patente-encabezado">
          <Escudo />
          <span className="patente-pais">ARGENTINA</span>
        </span>
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
