import { useState } from 'react'
import { FileText, Plus, Trash2, Upload, X } from 'lucide-react'
import { formatearFecha, hoyEnArgentina } from '../../utils/fechas.js'
import { TIPOS_INTERVENCION, formatearMiles, formatearTamano } from '../../utils/intervenciones.js'
import Campo from '../Campo.jsx'
import './FormularioIntervencion.css'

// Secciones del formulario de intervención. Reciben el objeto de useFormularioIntervencion().

const NOMBRE_TIPO = { 'application/pdf': 'PDF', 'image/jpeg': 'JPG', 'image/png': 'PNG' }

function soloDigitos(texto, maximo) {
  return texto.replace(/\D/g, '').slice(0, maximo)
}

// Kilometraje: mientras se edita muestra solo dígitos; al salir, con separador de miles.
export function CampoKilometraje({ id, valor, alCambiar, ...props }) {
  const [editando, setEditando] = useState(false)
  return (
    <Campo
      id={id}
      className="campo-mono"
      inputMode="numeric"
      autoComplete="off"
      sufijo="km"
      value={editando ? valor : formatearMiles(valor)}
      onFocus={() => setEditando(true)}
      onBlur={() => setEditando(false)}
      onChange={(evento) => alCambiar(soloDigitos(evento.target.value, 7))}
      {...props}
    />
  )
}

// `ultimaLectura`: { kilometraje, fecha } del vehículo, null si no tiene registros, undefined si no se sabe.
export function CamposServicio({ formulario, ultimaLectura }) {
  const { datos, errores, cambiar } = formulario
  const alCambiar = (evento) => cambiar(evento.target.name, evento.target.value)

  let ayudaKilometraje
  if (ultimaLectura) {
    const ultimo = `${formatearMiles(ultimaLectura.kilometraje)} km el ${formatearFecha(ultimaLectura.fecha)}`
    // Se puede registrar igual (HU-009): solo se avisa que va a quedar marcado.
    ayudaKilometraje =
      datos.kilometraje !== '' && Number(datos.kilometraje) < ultimaLectura.kilometraje ? (
        <span className="ayuda-ambar">
          Es menor al último registrado ({ultimo}): se va a guardar con una alerta de inconsistencia.
        </span>
      ) : (
        `Último registrado: ${ultimo}.`
      )
  } else if (ultimaLectura === null) {
    ayudaKilometraje = 'Todavía no hay kilometrajes registrados para este vehículo.'
  }

  return (
    <section className="seccion-intervencion" aria-labelledby="titulo-servicio">
      <h2 id="titulo-servicio">Datos del servicio</h2>
      <div className="fila-campos">
        <Campo
          id="fecha_intervencion"
          etiqueta="Fecha"
          type="date"
          className="campo-mono"
          max={hoyEnArgentina()}
          value={datos.fecha_intervencion}
          onChange={alCambiar}
          error={errores.fecha_intervencion}
        />
        <CampoKilometraje
          id="kilometraje"
          etiqueta="Kilometraje"
          valor={datos.kilometraje}
          alCambiar={(valor) => cambiar('kilometraje', valor)}
          error={errores.kilometraje}
          ayuda={ayudaKilometraje}
        />
      </div>
      <Campo
        id="tipo"
        etiqueta="Tipo de intervención"
        como="select"
        value={datos.tipo}
        onChange={alCambiar}
        error={errores.tipo}
      >
        <option value="">Elegí el tipo de intervención</option>
        {TIPOS_INTERVENCION.map((tipo) => (
          <option key={tipo}>{tipo}</option>
        ))}
      </Campo>
      <Campo
        id="descripcion"
        etiqueta="Descripción"
        como="textarea"
        rows={3}
        maxLength={1000}
        placeholder="Qué se hizo y en qué estado estaba el vehículo."
        value={datos.descripcion}
        onChange={alCambiar}
        error={errores.descripcion}
      />
    </section>
  )
}

export function ListaItems({ formulario, titulo }) {
  const { items, errores, cambiarItem, agregarItem, quitarItem } = formulario

  return (
    <section className="seccion-intervencion" aria-labelledby="titulo-items">
      <h2 id="titulo-items">{titulo}</h2>
      {errores.items && (
        <p className="campo-error items-error" role="alert">
          {errores.items}
        </p>
      )}
      {items.length > 0 && (
        <div className="items-encabezado" aria-hidden="true">
          <span>Descripción</span>
          <span>Cantidad</span>
        </div>
      )}
      <ul className="items">
        {items.map((item, i) => {
          const errorDescripcion = errores[`items.${i}.descripcion`]
          const errorCantidad = errores[`items.${i}.cantidad`]
          return (
            <li key={item.clave} className="item">
              <div className={`item-campo ${errorDescripcion ? 'campo-invalido' : ''}`}>
                <input
                  aria-label={`Descripción del ítem ${i + 1}`}
                  maxLength={200}
                  placeholder="Ej.: Filtro de aceite"
                  value={item.descripcion}
                  aria-invalid={Boolean(errorDescripcion)}
                  onChange={(evento) => cambiarItem(item.clave, 'descripcion', evento.target.value)}
                />
                {errorDescripcion && <p className="campo-error">{errorDescripcion}</p>}
              </div>
              <div className={`item-campo ${errorCantidad ? 'campo-invalido' : ''}`}>
                <input
                  aria-label={`Cantidad del ítem ${i + 1}`}
                  className="item-cantidad"
                  inputMode="numeric"
                  value={item.cantidad}
                  aria-invalid={Boolean(errorCantidad)}
                  onChange={(evento) => cambiarItem(item.clave, 'cantidad', soloDigitos(evento.target.value, 4))}
                />
                {errorCantidad && <p className="campo-error">{errorCantidad}</p>}
              </div>
              <button
                type="button"
                className="item-quitar"
                aria-label={`Quitar el ítem ${i + 1}`}
                onClick={() => quitarItem(item.clave)}
              >
                <Trash2 size={18} aria-hidden="true" />
              </button>
            </li>
          )
        })}
      </ul>
      <button type="button" className="boton-agregar" onClick={agregarItem}>
        <Plus size={18} aria-hidden="true" />
        Agregar ítem
      </button>
    </section>
  )
}

export function CamposProximaRevision({ formulario, ayuda, conDetalle = true }) {
  const { datos, errores, cambiar } = formulario
  const alCambiar = (evento) => cambiar(evento.target.name, evento.target.value)

  return (
    <section className="seccion-intervencion" aria-labelledby="titulo-proxima">
      <h2 id="titulo-proxima">Próxima revisión</h2>
      <p className="seccion-ayuda">{ayuda}</p>
      {errores.proxima_revision && (
        <p className="aviso aviso-error" role="alert">
          {errores.proxima_revision}
        </p>
      )}
      <div className="fila-campos">
        <CampoKilometraje
          id="proxima_revision.kilometraje"
          etiqueta="Kilometraje"
          placeholder="Ej.: 130000"
          valor={datos['proxima_revision.kilometraje']}
          alCambiar={(valor) => cambiar('proxima_revision.kilometraje', valor)}
          error={errores['proxima_revision.kilometraje']}
        />
        <Campo
          id="proxima_revision.fecha"
          etiqueta="Fecha"
          type="date"
          className="campo-mono"
          min={datos.fecha_intervencion || undefined}
          value={datos['proxima_revision.fecha']}
          onChange={alCambiar}
          error={errores['proxima_revision.fecha']}
        />
      </div>
      {conDetalle && (
        <Campo
          id="proxima_revision.detalle"
          etiqueta="Detalle"
          maxLength={200}
          placeholder="Ej.: Cambio de aceite y filtros"
          value={datos['proxima_revision.detalle']}
          onChange={alCambiar}
          error={errores['proxima_revision.detalle']}
        />
      )}
    </section>
  )
}

export function CampoComprobante({ formulario, ayuda }) {
  const { comprobante, errores, elegirComprobante } = formulario
  const [arrastrando, setArrastrando] = useState(false)

  return (
    <section className="seccion-intervencion" aria-labelledby="titulo-comprobante">
      <h2 id="titulo-comprobante">Comprobante</h2>
      <p className="seccion-ayuda">{ayuda}</p>
      <label
        className={`adjuntar ${arrastrando ? 'adjuntar-arrastrando' : ''} ${errores.comprobante ? 'adjuntar-invalido' : ''}`}
        onDragOver={(evento) => {
          evento.preventDefault()
          setArrastrando(true)
        }}
        onDragLeave={() => setArrastrando(false)}
        onDrop={(evento) => {
          evento.preventDefault()
          setArrastrando(false)
          elegirComprobante(evento.dataTransfer.files[0] ?? null)
        }}
      >
        <input
          type="file"
          className="visualmente-oculto"
          accept=".pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png"
          aria-describedby="comprobante-mensaje"
          onChange={(evento) => {
            elegirComprobante(evento.target.files[0] ?? null)
            evento.target.value = ''
          }}
        />
        <span className="adjuntar-icono">
          <Upload size={20} aria-hidden="true" />
        </span>
        <strong>Adjuntar comprobante</strong>
        <span id="comprobante-mensaje">Factura o ticket de los insumos · PDF, JPG o PNG hasta 5 MB</span>
      </label>
      {errores.comprobante && (
        <p className="campo-error" role="alert">
          {errores.comprobante}
        </p>
      )}
      {comprobante && (
        <div className="archivo-adjunto">
          <FileText size={22} aria-hidden="true" />
          <div>
            <strong>{comprobante.name}</strong>
            <span>
              {NOMBRE_TIPO[comprobante.type]} · {formatearTamano(comprobante.size)}
            </span>
          </div>
          <button
            type="button"
            className="archivo-quitar"
            aria-label="Quitar el comprobante"
            onClick={() => elegirComprobante(null)}
          >
            <X size={20} aria-hidden="true" />
          </button>
        </div>
      )}
    </section>
  )
}
