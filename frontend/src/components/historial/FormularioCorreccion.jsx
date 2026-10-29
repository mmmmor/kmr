import { useState } from 'react'
import { CircleAlert, Link2, TriangleAlert } from 'lucide-react'
import { corregirIntervencion } from '../../api/intervenciones.js'
import { fechaEnArgentina, formatearFecha, hoyEnArgentina } from '../../utils/fechas.js'
import {
  TIPOS_INTERVENCION,
  formatearMiles,
  textoAlertaKilometraje,
  tituloCorreccion,
} from '../../utils/intervenciones.js'
import Badge from '../Badge.jsx'
import Campo from '../Campo.jsx'
import Patente from '../Patente.jsx'
import { CampoKilometraje } from '../intervencion/SeccionesIntervencion.jsx'
import './FormularioCorreccion.css'

// Datos que se pueden corregir desde el panel, con cómo se muestran y se editan.
const DATOS = {
  kilometraje: { nombre: 'Kilometraje', mostrar: (v) => `${formatearMiles(v)} km`, aValor: String },
  fecha_intervencion: { nombre: 'Fecha del servicio', mostrar: formatearFecha, aValor: fechaEnArgentina },
  tipo: { nombre: 'Tipo de intervención', mostrar: (v) => v, aValor: (v) => v },
  descripcion: { nombre: 'Descripción', mostrar: (v) => v || 'Sin descripción', aValor: (v) => v ?? '' },
}

// La API recibe los datos completos del registro ya corregidos: se parte del original.
function datosDelRegistro(intervencion) {
  const proxima = intervencion.proxima_revision
  return {
    fecha_intervencion: fechaEnArgentina(intervencion.fecha_intervencion),
    kilometraje: intervencion.kilometraje,
    tipo: intervencion.tipo,
    descripcion: intervencion.descripcion,
    items: intervencion.items,
    proxima_revision: proxima && { ...proxima, fecha: proxima.fecha && fechaEnArgentina(proxima.fecha) },
  }
}

function ValorCorrecto({ dato, valor, alCambiar, error }) {
  const comun = { id: 'valor', etiqueta: 'Valor correcto', error }
  if (dato === 'kilometraje') return <CampoKilometraje {...comun} valor={valor} alCambiar={alCambiar} />
  if (dato === 'fecha_intervencion') {
    return (
      <Campo
        {...comun}
        type="date"
        className="campo-mono"
        max={hoyEnArgentina()}
        value={valor}
        onChange={(e) => alCambiar(e.target.value)}
      />
    )
  }
  if (dato === 'tipo') {
    return (
      <Campo {...comun} como="select" value={valor} onChange={(e) => alCambiar(e.target.value)}>
        {TIPOS_INTERVENCION.map((tipo) => (
          <option key={tipo}>{tipo}</option>
        ))}
      </Campo>
    )
  }
  return (
    <Campo
      {...comun}
      como="textarea"
      rows={3}
      maxLength={1000}
      value={valor}
      onChange={(e) => alCambiar(e.target.value)}
    />
  )
}

// Panel "Registrar corrección vinculada" (HU-011). El original no se modifica: la corrección es
// un registro nuevo vinculado a él, y los dos se ven en el historial.
function FormularioCorreccion({ intervencion, alCorregir, alCancelar }) {
  const [dato, setDato] = useState('kilometraje')
  const [valor, setValor] = useState('')
  const [motivo, setMotivo] = useState('')
  const [errores, setErrores] = useState({})
  const [errorGeneral, setErrorGeneral] = useState('')
  const [enviando, setEnviando] = useState(false)

  const original = DATOS[dato].aValor(intervencion[dato])
  const esCorreccion = Boolean(intervencion.corrige_a)

  function elegirDato(nuevo) {
    setDato(nuevo)
    // El tipo arranca en el registrado (es una lista); el resto, vacío para escribir el correcto.
    setValor(nuevo === 'tipo' ? intervencion.tipo : '')
    setErrores({})
  }

  async function enviar(evento) {
    evento.preventDefault()
    setErrorGeneral('')
    const faltantes = {}
    if (dato !== 'descripcion' && !valor.trim()) faltantes.valor = 'Completá este campo.'
    else if (valor.trim() === String(original).trim()) faltantes.valor = 'Es igual al valor registrado.'
    if (!motivo.trim()) faltantes.motivo = 'Completá este campo.'
    if (Object.keys(faltantes).length > 0) {
      setErrores(faltantes)
      return
    }

    const corregido = dato === 'kilometraje' ? Number(valor) : valor.trim() || null
    setEnviando(true)
    try {
      const datos = { ...datosDelRegistro(intervencion), [dato]: corregido, motivo }
      alCorregir(await corregirIntervencion(intervencion.id, datos))
    } catch (error) {
      const campos = error.campos ?? {}
      const enPanel = { valor: campos[dato], motivo: campos.motivo }
      setErrores(enPanel)
      if (!enPanel.valor && !enPanel.motivo) setErrorGeneral(error.message)
      setEnviando(false)
    }
  }

  return (
    <form className="deslizable-formulario correccion" onSubmit={enviar} noValidate>
      <p className="correccion-texto">
        El registro original no se modifica. La corrección se guarda como un registro nuevo, vinculado al
        original, y ambos se muestran en el historial del vehículo.
      </p>

      {errorGeneral && (
        <p className="aviso aviso-error" role="alert">
          <CircleAlert size={18} aria-hidden="true" />
          {errorGeneral}
        </p>
      )}

      <section className="correccion-original" aria-label="Registro original">
        <p className="correccion-etiqueta">Registro original</p>
        <div className="correccion-original-datos">
          <Patente dominio={intervencion.dominio} tamano="chico" />
          <div>
            <strong>{esCorreccion ? tituloCorreccion(intervencion.campos_corregidos) : intervencion.tipo}</strong>
            <span className="correccion-original-fecha mono">
              {formatearFecha(intervencion.fecha_intervencion)} · {formatearMiles(intervencion.kilometraje)} km
            </span>
          </div>
        </div>
        {intervencion.alerta_kilometraje && (
          <Badge tipo="ambar" Icono={TriangleAlert}>
            {textoAlertaKilometraje(intervencion.alerta_kilometraje)}
          </Badge>
        )}
      </section>

      <Campo id="dato" etiqueta="Dato a corregir" como="select" value={dato} onChange={(e) => elegirDato(e.target.value)}>
        {Object.entries(DATOS).map(([clave, { nombre }]) => (
          <option key={clave} value={clave}>
            {nombre}
          </option>
        ))}
      </Campo>

      <div className={dato === 'descripcion' ? 'correccion-valores apilados' : 'correccion-valores'}>
        <div className="campo">
          <div className="campo-etiqueta">
            <span id="valor-registrado-etiqueta" className="correccion-etiqueta-campo">
              Valor registrado
            </span>
          </div>
          <p className="correccion-registrado" aria-labelledby="valor-registrado-etiqueta">
            {DATOS[dato].mostrar(intervencion[dato])}
          </p>
        </div>
        <ValorCorrecto
          dato={dato}
          valor={valor}
          alCambiar={(nuevo) => {
            setValor(nuevo)
            setErrores((anteriores) => ({ ...anteriores, valor: undefined }))
          }}
          error={errores.valor}
        />
      </div>

      <Campo
        id="motivo"
        etiqueta={
          <>
            Motivo de la corrección <span className="correccion-obligatorio">(obligatorio)</span>
          </>
        }
        como="textarea"
        rows={4}
        maxLength={500}
        value={motivo}
        onChange={(e) => {
          setMotivo(e.target.value)
          setErrores((anteriores) => ({ ...anteriores, motivo: undefined }))
        }}
        error={errores.motivo}
        ayuda="Se muestra junto a la corrección en el historial."
      />

      <div className="deslizable-pie">
        <button type="button" className="boton-secundario" onClick={alCancelar}>
          Cancelar
        </button>
        <button type="submit" className="boton-primario boton-ajustado" disabled={enviando}>
          <Link2 size={18} aria-hidden="true" />
          {enviando ? 'Registrando…' : 'Registrar corrección'}
        </button>
      </div>
    </form>
  )
}

export default FormularioCorreccion
