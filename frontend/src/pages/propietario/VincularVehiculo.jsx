import { useState } from 'react'
import { CircleAlert } from 'lucide-react'
import { vincularVehiculo } from '../../api/vehiculos.js'
import Campo from '../../components/Campo.jsx'
import Patente from '../../components/Patente.jsx'
import { formatoDominio, normalizarDominio } from '../../utils/dominio.js'

const VACIO = { dominio: '', marca: '', modelo: '', anio: '' }

const NOMBRE_FORMATO = {
  mercosur: 'Formato Mercosur (desde 2016)',
  anterior: 'Formato anterior (1995 a 2016)',
}

// Formulario del panel "Vincular vehículo" (HU-005).
function VincularVehiculo({ alVincular, alCancelar }) {
  const [datos, setDatos] = useState(VACIO)
  const [declara, setDeclara] = useState(false)
  const [errores, setErrores] = useState({})
  const [errorGeneral, setErrorGeneral] = useState('')
  const [enviando, setEnviando] = useState(false)

  const formato = formatoDominio(datos.dominio)

  function cambiar(evento) {
    const { name, value } = evento.target
    let valor = value
    if (name === 'dominio') valor = normalizarDominio(value).slice(0, 7)
    if (name === 'anio') valor = value.replace(/\D/g, '').slice(0, 4)
    setDatos((anteriores) => ({ ...anteriores, [name]: valor }))
    setErrores((anteriores) => ({ ...anteriores, [name]: undefined }))
  }

  async function enviar(evento) {
    evento.preventDefault()
    setErrorGeneral('')

    const faltantes = Object.fromEntries(
      Object.entries(datos)
        .filter(([, valor]) => !valor.trim())
        .map(([campo]) => [campo, 'Completá este campo.']),
    )
    if (!declara) faltantes.declara = 'Confirmá que sos titular o usuario autorizado del vehículo.'
    if (Object.keys(faltantes).length > 0) {
      setErrores(faltantes)
      return
    }

    setEnviando(true)
    try {
      alVincular(await vincularVehiculo({ ...datos, anio: Number(datos.anio) }))
    } catch (error) {
      const campos = error.campos ?? {}
      setErrores(campos)
      if (Object.keys(campos).length === 0) setErrorGeneral(error.message)
      setEnviando(false)
    }
  }

  return (
    <form className="deslizable-formulario" onSubmit={enviar} noValidate>
      <p className="vincular-texto">
        Ingresá el dominio tal como figura en la patente. El formato se reconoce automáticamente.
      </p>

      {errorGeneral && (
        <p className="aviso aviso-error" role="alert">
          <CircleAlert size={18} aria-hidden="true" />
          {errorGeneral}
        </p>
      )}

      <Campo
        id="dominio"
        etiqueta="Dominio"
        className="campo-mono campo-dominio"
        autoComplete="off"
        autoCapitalize="characters"
        spellCheck={false}
        placeholder="AA123BB"
        value={datos.dominio}
        onChange={cambiar}
        error={errores.dominio}
        autoFocus
      />

      <div className={`vista-patente ${formato ? '' : 'vista-patente-vacia'}`}>
        {formato && <Patente dominio={datos.dominio} tamano="grande" />}
        <p aria-live="polite">
          {formato
            ? NOMBRE_FORMATO[formato]
            : 'Formatos válidos: AAA 111 (anterior) o AA 111 AA (Mercosur).'}
        </p>
      </div>

      <div className="fila-campos">
        <Campo id="marca" etiqueta="Marca" value={datos.marca} onChange={cambiar} error={errores.marca} />
        <Campo id="modelo" etiqueta="Modelo" value={datos.modelo} onChange={cambiar} error={errores.modelo} />
      </div>
      <div className="fila-campos">
        <Campo
          id="anio"
          etiqueta="Año"
          className="campo-mono"
          inputMode="numeric"
          value={datos.anio}
          onChange={cambiar}
          error={errores.anio}
        />
      </div>

      <label className="casilla vincular-declaracion">
        <input
          type="checkbox"
          checked={declara}
          aria-invalid={Boolean(errores.declara)}
          aria-describedby={errores.declara ? 'declara-mensaje' : undefined}
          onChange={(evento) => {
            setDeclara(evento.target.checked)
            setErrores((anteriores) => ({ ...anteriores, declara: undefined }))
          }}
        />
        Declaro ser titular o usuario autorizado de este vehículo.
      </label>
      {errores.declara && (
        <p id="declara-mensaje" className="campo-error">
          {errores.declara}
        </p>
      )}

      <div className="deslizable-pie">
        <button type="button" className="boton-secundario" onClick={alCancelar}>
          Cancelar
        </button>
        <button type="submit" className="boton-primario boton-ajustado" disabled={enviando}>
          {enviando ? 'Vinculando…' : 'Vincular vehículo'}
        </button>
      </div>
    </form>
  )
}

export default VincularVehiculo
