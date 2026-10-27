import './formulario.css'

// Input con etiqueta, ayuda opcional y mensaje de error accesible.
function Campo({ id, etiqueta, error, ayuda, accesorio, ...props }) {
  return (
    <div className={`campo ${error ? 'campo-invalido' : ''}`}>
      <div className="campo-etiqueta">
        <label htmlFor={id}>{etiqueta}</label>
        {accesorio}
      </div>
      <input
        id={id}
        name={id}
        aria-invalid={Boolean(error)}
        aria-describedby={error || ayuda ? `${id}-mensaje` : undefined}
        {...props}
      />
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
