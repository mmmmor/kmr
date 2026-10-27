import { useState } from 'react'
import { Check, CircleX, Clock, Copy, ExternalLink } from 'lucide-react'
import { aprobarSolicitud, rechazarSolicitud } from '../../api/admin.js'
import { formatearCuit } from '../../utils/cuit.js'
import { formatearFechaHora } from '../../utils/fechas.js'

// Consulta pública de la constancia de inscripción de ARCA. No admite precargar el CUIT.
const URL_CONSTANCIA_ARCA = 'https://seti.afip.gob.ar/padron-puc-constancia-internet/ConsultaConstanciaAction.do'

const VERIFICACIONES = [
  'El CUIT figura activo en ARCA.',
  'La razón social coincide con la informada.',
  'La actividad registrada corresponde a mantenimiento o reparación de vehículos.',
]

const ESTADOS = {
  pendiente: { texto: 'Pendiente de revisión', corto: 'Pendiente', clase: 'estado-pendiente', Icono: Clock },
  aprobado: { texto: 'Aprobada', corto: 'Aprobada', clase: 'estado-aprobado', Icono: Check },
  rechazado: { texto: 'Rechazada', corto: 'Rechazada', clase: 'estado-rechazado', Icono: CircleX },
}

export function EstadoSolicitud({ estado, compacto = false }) {
  const { texto, corto, clase, Icono } = ESTADOS[estado]
  return (
    <span className={`estado-solicitud ${clase}`}>
      {!compacto && <Icono size={15} aria-hidden="true" />}
      {compacto ? corto : texto}
    </span>
  )
}

function Dato({ etiqueta, children, mono = false }) {
  return (
    <div className="detalle-dato">
      <dt>{etiqueta}</dt>
      <dd className={mono ? 'mono' : undefined}>{children}</dd>
    </div>
  )
}

function DetalleSolicitud({ solicitud, alResolver }) {
  const [verificadas, setVerificadas] = useState(VERIFICACIONES.map(() => false))
  const [rechazando, setRechazando] = useState(false)
  const [motivo, setMotivo] = useState('')
  const [errorMotivo, setErrorMotivo] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [copiado, setCopiado] = useState(false)

  const cuit = formatearCuit(solicitud.cuit)
  const pendiente = solicitud.estado_solicitud === 'pendiente'
  const todasVerificadas = verificadas.every(Boolean)

  async function resolver(accion, textoExito) {
    setEnviando(true)
    try {
      await accion()
      alResolver({ tipo: 'exito', texto: textoExito })
    } catch (error) {
      if (error.campos?.motivo) {
        setErrorMotivo(error.campos.motivo)
      } else {
        alResolver({ tipo: 'error', texto: error.message })
      }
    } finally {
      setEnviando(false)
    }
  }

  function aprobar() {
    resolver(
      () => aprobarSolicitud(solicitud.id),
      `Aprobaste la solicitud de ${solicitud.razon_social}. El taller ya puede iniciar sesión.`,
    )
  }

  function confirmarRechazo(evento) {
    evento.preventDefault()
    if (!motivo.trim()) {
      setErrorMotivo('Indicá el motivo del rechazo.')
      return
    }
    resolver(
      () => rechazarSolicitud(solicitud.id, motivo),
      `Rechazaste la solicitud de ${solicitud.razon_social}. El taller verá el motivo al intentar iniciar sesión.`,
    )
  }

  async function copiarCuit() {
    try {
      await navigator.clipboard.writeText(solicitud.cuit)
      setCopiado(true)
      setTimeout(() => setCopiado(false), 2000)
    } catch {
      // Sin permiso de portapapeles: el CUIT igual queda visible para copiarlo a mano.
    }
  }

  const { responsable } = solicitud

  return (
    <article className="detalle" aria-labelledby="detalle-titulo">
      <header className="detalle-encabezado">
        <div>
          <h2 id="detalle-titulo">{solicitud.razon_social}</h2>
          <p>Solicitud recibida el {formatearFechaHora(solicitud.fecha_solicitud)}</p>
        </div>
        <EstadoSolicitud estado={solicitud.estado_solicitud} />
      </header>

      <dl className="detalle-datos">
        <Dato etiqueta="Razón social">{solicitud.razon_social}</Dato>
        <Dato etiqueta="CUIT" mono>
          {cuit}
        </Dato>
        <Dato etiqueta="Domicilio del establecimiento">{solicitud.domicilio}</Dato>
        <Dato etiqueta="Teléfono">{solicitud.telefono}</Dato>
        <Dato etiqueta="Responsable">
          {responsable.nombre} {responsable.apellido}
        </Dato>
        <Dato etiqueta="Correo electrónico">{responsable.correo}</Dato>
      </dl>

      {!pendiente && (
        <div className={`detalle-resolucion ${solicitud.estado_solicitud}`}>
          <p>
            {solicitud.estado_solicitud === 'aprobado' ? 'Aprobada' : 'Rechazada'} el{' '}
            {formatearFechaHora(solicitud.fecha_resolucion)}.
          </p>
          {solicitud.motivo_rechazo && (
            <p>
              <strong>Motivo:</strong> {solicitud.motivo_rechazo}
            </p>
          )}
        </div>
      )}

      {pendiente && (
        <>
          <section className="verificacion" aria-labelledby="verificacion-titulo">
            <div className="verificacion-encabezado">
              <div>
                <h3 id="verificacion-titulo">Verificación en ARCA</h3>
                <p>
                  Consultá la constancia de inscripción del CUIT <span className="mono">{cuit}</span> y
                  compará los datos.
                </p>
              </div>
              <div className="verificacion-acciones">
                <a className="boton-secundario" href={URL_CONSTANCIA_ARCA} target="_blank" rel="noopener noreferrer">
                  Abrir constancia
                  <ExternalLink size={16} aria-hidden="true" />
                </a>
                <button type="button" className="boton-texto" onClick={copiarCuit}>
                  <Copy size={14} aria-hidden="true" />
                  {copiado ? 'CUIT copiado' : 'Copiar CUIT'}
                </button>
              </div>
            </div>
            <fieldset className="verificacion-lista">
              <legend>Datos verificados</legend>
              {VERIFICACIONES.map((texto, i) => (
                <label key={texto} className="casilla">
                  <input
                    type="checkbox"
                    checked={verificadas[i]}
                    onChange={() => setVerificadas((v) => v.map((x, j) => (j === i ? !x : x)))}
                  />
                  {texto}
                </label>
              ))}
            </fieldset>
          </section>

          {rechazando ? (
            <form className="rechazo" onSubmit={confirmarRechazo} noValidate>
              <label htmlFor="motivo">Motivo del rechazo</label>
              <textarea
                id="motivo"
                rows={3}
                maxLength={500}
                value={motivo}
                aria-invalid={Boolean(errorMotivo)}
                aria-describedby="motivo-mensaje"
                placeholder="Por ejemplo: la razón social no coincide con la constancia de ARCA."
                onChange={(e) => {
                  setMotivo(e.target.value)
                  setErrorMotivo('')
                }}
                autoFocus
              />
              <p id="motivo-mensaje" className={errorMotivo ? 'campo-error' : 'campo-ayuda'}>
                {errorMotivo || 'El taller va a ver este motivo cuando intente iniciar sesión.'}
              </p>
              <div className="detalle-acciones">
                <button type="button" className="boton-secundario" onClick={() => setRechazando(false)}>
                  Cancelar
                </button>
                <button type="submit" className="boton-peligro" disabled={enviando}>
                  <CircleX size={18} aria-hidden="true" />
                  {enviando ? 'Rechazando…' : 'Confirmar rechazo'}
                </button>
              </div>
            </form>
          ) : (
            <div className="detalle-acciones">
              <button type="button" className="boton-peligro-contorno" onClick={() => setRechazando(true)}>
                <CircleX size={18} aria-hidden="true" />
                Rechazar
              </button>
              <button
                type="button"
                className="boton-aprobar"
                disabled={!todasVerificadas || enviando}
                onClick={aprobar}
              >
                <Check size={18} aria-hidden="true" />
                {enviando ? 'Aprobando…' : 'Aprobar solicitud'}
              </button>
              <p className="detalle-acciones-nota">
                Para aprobar, marcá las tres verificaciones. El taller podrá iniciar sesión en cuanto la
                apruebes.
              </p>
            </div>
          )}
        </>
      )}
    </article>
  )
}

export default DetalleSolicitud
