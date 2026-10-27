import { useEffect, useRef, useState } from 'react'
import { CircleAlert, CircleCheck, Inbox, Search } from 'lucide-react'
import { listarSolicitudes } from '../../api/admin.js'
import LayoutPanel from '../../components/LayoutPanel.jsx'
import { formatearCuit } from '../../utils/cuit.js'
import { formatearFechaHora } from '../../utils/fechas.js'
import DetalleSolicitud, { EstadoSolicitud } from './DetalleSolicitud.jsx'
import '../../components/formulario.css'
import './Solicitudes.css'

const PESTANAS = [
  { estado: 'pendiente', texto: 'Pendientes', titulo: 'Pendientes de revisión', vacio: 'No hay solicitudes pendientes' },
  { estado: 'aprobado', texto: 'Aprobadas', titulo: 'Solicitudes aprobadas', vacio: 'Todavía no hay solicitudes aprobadas.' },
  { estado: 'rechazado', texto: 'Rechazadas', titulo: 'Solicitudes rechazadas', vacio: 'No hay solicitudes rechazadas.' },
]

// Panel del administrador: aprobar o rechazar las solicitudes de alta de talleres (HU-004).
function Solicitudes() {
  const [pestana, setPestana] = useState('pendiente')
  const [cargadas, setCargadas] = useState({ pestana: null, lista: [] })
  const [cantidadPendientes, setCantidadPendientes] = useState(null)
  const [recarga, setRecarga] = useState(0)
  const [seleccionadaId, setSeleccionadaId] = useState(null)
  const [aviso, setAviso] = useState(null)
  const [errorCarga, setErrorCarga] = useState('')
  const detalle = useRef(null)

  useEffect(() => {
    let vigente = true
    listarSolicitudes(pestana)
      .then((lista) => {
        if (!vigente) return
        setCargadas({ pestana, lista })
        setErrorCarga('')
        if (pestana === 'pendiente') setCantidadPendientes(lista.length)
      })
      .catch((error) => vigente && setErrorCarga(error.message))
    return () => {
      vigente = false
    }
  }, [pestana, recarga])

  // El contador de pendientes se ve en la barra lateral y en la pestaña aunque se mire otra.
  useEffect(() => {
    let vigente = true
    listarSolicitudes('pendiente')
      .then((lista) => vigente && setCantidadPendientes(lista.length))
      .catch(() => {})
    return () => {
      vigente = false
    }
  }, [recarga])

  const actual = PESTANAS.find((p) => p.estado === pestana)
  const cargando = cargadas.pestana !== pestana && !errorCarga
  const lista = cargadas.pestana === pestana ? cargadas.lista : []
  const seleccionada = lista.find((s) => s.id === seleccionadaId) ?? lista[0]

  function cambiarPestana(estado) {
    setPestana(estado)
    setSeleccionadaId(null)
    setAviso(null)
  }

  function seleccionar(id) {
    setSeleccionadaId(id)
    setAviso(null)
    if (window.matchMedia('(max-width: 900px)').matches) {
      requestAnimationFrame(() => detalle.current?.scrollIntoView({ behavior: 'smooth' }))
    }
  }

  function alResolver(resultado) {
    setAviso(resultado)
    setSeleccionadaId(null)
    setRecarga((n) => n + 1)
  }

  const enlaces = [
    { a: '/admin', texto: 'Solicitudes de talleres', Icono: Inbox, insignia: cantidadPendientes },
    { a: '/', texto: 'Consulta pública', Icono: Search },
  ]

  return (
    <LayoutPanel enlaces={enlaces}>
      <h1 className="titulo-pagina">Solicitudes de alta de talleres</h1>
      <p className="subtitulo-pagina">
        Verificá cada establecimiento contra la constancia de inscripción de ARCA antes de aprobarlo.
      </p>

      <div className="pestanas" role="tablist">
        {PESTANAS.map(({ estado, texto }) => (
          <button
            key={estado}
            type="button"
            role="tab"
            aria-selected={pestana === estado}
            className={`pestana ${pestana === estado ? 'activa' : ''}`}
            onClick={() => cambiarPestana(estado)}
          >
            {texto}
            {estado === 'pendiente' && cantidadPendientes !== null && ` (${cantidadPendientes})`}
          </button>
        ))}
      </div>

      {aviso && (
        <p className={`aviso aviso-${aviso.tipo}`} role={aviso.tipo === 'error' ? 'alert' : 'status'}>
          {aviso.tipo === 'error' ? (
            <CircleAlert size={18} aria-hidden="true" />
          ) : (
            <CircleCheck size={18} aria-hidden="true" />
          )}
          {aviso.texto}
        </p>
      )}
      {errorCarga && (
        <p className="aviso aviso-error" role="alert">
          <CircleAlert size={18} aria-hidden="true" />
          {errorCarga}
        </p>
      )}

      {cargando ? (
        <p className="solicitudes-cargando">Cargando solicitudes…</p>
      ) : (
        !errorCarga &&
        (lista.length === 0 ? (
          <div className="solicitudes-vacio">
            <Inbox size={32} aria-hidden="true" />
            <p>{actual.vacio}</p>
          </div>
        ) : (
          <div className="solicitudes">
            <section aria-labelledby="titulo-lista">
              <h2 id="titulo-lista" className="solicitudes-titulo">
                {actual.titulo}
              </h2>
              <ul className="solicitudes-lista">
                {lista.map((s) => (
                  <li key={s.id}>
                    <button
                      type="button"
                      className={`solicitud-item ${s.id === seleccionada?.id ? 'activa' : ''}`}
                      aria-current={s.id === seleccionada?.id}
                      onClick={() => seleccionar(s.id)}
                    >
                      <strong>{s.razon_social}</strong>
                      <span className="mono">CUIT {formatearCuit(s.cuit)}</span>
                      <span className="solicitud-item-pie">
                        <span>{formatearFechaHora(s.fecha_solicitud)}</span>
                        <EstadoSolicitud estado={s.estado_solicitud} compacto />
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            </section>
            <div ref={detalle}>
              {seleccionada && (
                <DetalleSolicitud key={seleccionada.id} solicitud={seleccionada} alResolver={alResolver} />
              )}
            </div>
          </div>
        ))
      )}
    </LayoutPanel>
  )
}

export default Solicitudes
