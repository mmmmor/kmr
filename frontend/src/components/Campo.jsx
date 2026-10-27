import './formulario.css'

// Campo con etiqueta, ayuda opcional y mensaje de error accesible.
// `como`: 'input' (por defecto), 'select' o 'textarea'. `sufijo`: texto fijo a la derecha (ej. "km").
function Campo({ id, etiqueta, error, ayuda, accesorio, sufijo, como: Control = 'input', children, ...props }) {
  const control = (
    <Control
      id={id}
      name={id}
      aria-invalid={Boolean(error)}
      aria-describedby={error || ayuda ? `${id}-mensaje` : undefined}
      {...props}
    >
      {children}
    </Control>
  )

  return (
    <div className={`campo ${error ? 'campo-invalido' : ''}`}>
      <div className="campo-etiqueta">
        <label htmlFor={id}>{etiqueta}</label>
        {accesorio}
      </div>
      {sufijo ? (
        <div className="campo-con-sufijo">
          {control}
          <span className="campo-sufijo" aria-hidden="true">
            {sufijo}
          </span>
        </div>
      ) : (
        control
      )}
      {error ? (
        <p id={`${id}-mensaje`} className="campo-error">
          {error}
        </p>
      ) : (
        ayuda && (
          <p id={`${id}-mensaje`} className="campo-ayuda">
            {ayuda}
          </p>
        )
      )}
    </div>
  )
}

export default Campo
