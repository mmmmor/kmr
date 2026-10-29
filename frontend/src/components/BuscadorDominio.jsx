import { useState } from 'react'
import { Search } from 'lucide-react'
import { useNavigate } from 'react-router'
import { formatoDominio, normalizarDominio } from '../utils/dominio.js'
import './BuscadorDominio.css'

// Buscador de la consulta pública. `variante`: 'grande' (inicio) o 'compacto' (encabezado del resultado).
function BuscadorDominio({ variante = 'grande', inicial = '' }) {
  const navigate = useNavigate()
  const [dominio, setDominio] = useState(inicial)
  const [error, setError] = useState('')
  const id = `dominio-${variante}`

  function consultar(evento) {
    evento.preventDefault()
    if (!dominio) {
      setError('Ingresá el dominio del vehículo.')
      return
    }
    if (!formatoDominio(dominio)) {
      setError('El dominio no es válido: usá el formato AAA 111 o AA 111 AA.')
      return
    }
    navigate(`/consulta/${dominio}`)
  }

  return (
    <form className={`buscador buscador-${variante}`} role="search" onSubmit={consultar} noValidate>
      <div className={`buscador-caja ${error ? 'buscador-invalido' : ''}`}>
        <label htmlFor={id}>Dominio</label>
        <input
          id={id}
          className="mono"
          placeholder="AE123CD"
          autoComplete="off"
          autoCapitalize="characters"
          spellCheck={false}
          value={dominio}
          aria-invalid={Boolean(error)}
          aria-describedby={error ? `${id}-error` : undefined}
          onChange={(evento) => {
            setDominio(normalizarDominio(evento.target.value).slice(0, 7))
            setError('')
          }}
        />
        <button type="submit" className="boton-primario boton-ajustado">
          <Search size={18} aria-hidden="true" />
          {variante === 'grande' ? 'Consultar historial' : 'Consultar'}
        </button>
      </div>
      {error && (
        <p id={`${id}-error`} className="campo-error buscador-error" role="alert">
          {error}
        </p>
      )}
    </form>
  )
}

export default BuscadorDominio
