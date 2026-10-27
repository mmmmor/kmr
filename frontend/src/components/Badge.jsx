import './Badge.css'

// Etiqueta redondeada. `tipo`: 'exito' (verde), 'ambar', 'error' o 'neutro'.
function Badge({ tipo = 'neutro', Icono, children }) {
  return (
    <span className={`badge badge-${tipo}`}>
      {Icono && <Icono size={14} strokeWidth={2.4} aria-hidden="true" />}
      {children}
    </span>
  )
}

export default Badge
