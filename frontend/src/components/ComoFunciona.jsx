import './ComoFunciona.css'

// Tarjeta lateral con reglas o pasos, cada uno con su ícono. `items`: [{ Icono, texto }]
function ComoFunciona({ titulo, items, pie, className = '' }) {
  return (
    <aside className={`como-funciona ${className}`}>
      <h2>{titulo}</h2>
      <ul>
        {items.map(({ Icono, texto }) => (
          <li key={texto}>
            <span className="como-funciona-icono">
              <Icono size={18} aria-hidden="true" />
            </span>
            {texto}
          </li>
        ))}
      </ul>
      {pie && <p className="como-funciona-pie">{pie}</p>}
    </aside>
  )
}

export default ComoFunciona
