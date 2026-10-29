import { useEffect, useState } from 'react'
import { CircleAlert, CircleCheck, ClipboardList, FilePen, FileText, Link2, TriangleAlert } from 'lucide-react'
import { Link } from 'react-router'
import { abrirComprobante } from '../../api/intervenciones.js'
import { listarRegistros } from '../../api/taller.js'
import Campo from '../../components/Campo.jsx'
import LayoutPanel from '../../components/LayoutPanel.jsx'
import PanelDeslizable from '../../components/PanelDeslizable.jsx'
import Patente from '../../components/Patente.jsx'
import FormularioCorreccion from '../../components/historial/FormularioCorreccion.jsx'
import { formatearDominio, normalizarDominio } from '../../utils/dominio.js'
import { formatearFecha } from '../../utils/fechas.js'
import { formatearMiles, textoAlertaKilometraje, tituloCorreccion } from '../../utils/intervenciones.js'
import { ENLACES_TALLER } from './navegacion.js'
import '../../components/formulario.css'
import './RegistrosRealizados.css'

const ESTADOS = {
  todos: { nombre: 'Todos', incluye: () => true },
  alerta: { nombre: 'Con alerta de kilometraje', incluye: (r) => Boolean(r.alerta_kilometraje) },
  correccion: { nombre: 'Con corrección', incluye: (r) => Boolean(r.corrige_a || r.corregido_por) },
}

function Registro({ registro, alVerComprobante, alCorregir }) {
  const { alerta_kilometraje: alerta, corrige_a: corrige, corregido_por: corregidoPor } = registro
  return (
    <tr>
      <td className="tabla-registros-fecha mono">{formatearFecha(registro.fecha)}</td>
      <td className="tabla-registros-dominio">
        <Patente dominio={registro.dominio} tamano="chico" />
      </td>
      <td className="tabla-registros-intervencion">
        <strong>{corrige ? tituloCorreccion(registro.campos_corregidos) : registro.tipo}</strong>
        {alerta && (
          <span className="tabla-registros-alerta">
            <TriangleAlert size={14} aria-hidden="true" />
            {textoAlertaKilometraje(alerta)}
          </span>
        )}
        {corrige && (
          <span className="tabla-registros-vinculo">
            <Link2 size={14} aria-hidden="true" />
            Corrige el registro del {formatearFecha(corrige.fecha)}
          </span>
        )}
        {corregidoPor && (
          <span className="tabla-registros-vinculo">
            <Link2 size={14} aria-hidden="true" />
            Corregido por el registro del {formatearFecha(corregidoPor.fecha)}
          </span>
        )}
        {!corrige && registro.descripcion && <span>{registro.descripcion}</span>}
      </td>
      <td className={`tabla-registros-km mono ${alerta ? 'km-alerta' : ''}`}>
        {formatearMiles(registro.kilometraje)} km
      </td>
      <td className="tabla-registros-acciones">
        {registro.tiene_comprobante && (
          <button type="button" className="boton-texto" onClick={() => alVerComprobante(registro.id)}>
            <FileText size={16} aria-hidden="true" />
            Ver comprobante
          </button>
        )}
        {/* Un registro ya corregido no se vuelve a corregir: si hay otro error, se corrige la corrección. */}
        {!corregidoPor && (
          <button type="button" className="boton-texto" onClick={() => alCorregir(registro)}>
            <FilePen size={16} aria-hidden="true" />
            Corregir
          </button>
        )}
      </td>
    </tr>
  )
}

// Intervenciones registradas por el taller, de la más reciente a la más antigua, con sus correcciones (HU-011).
function RegistrosRealizados() {
  const [registros, setRegistros] = useState(null)
  const [error, setError] = useState('')
  const [aviso, setAviso] = useState('')
  const [busqueda, setBusqueda] = useState('')
  const [estado, setEstado] = useState('todos')
  const [corrigiendo, setCorrigiendo] = useState(null)

  useEffect(() => {
    let vigente = true
    listarRegistros()
      .then((lista) => vigente && setRegistros(lista))
      .catch((e) => vigente && setError(e.message))
    return () => {
      vigente = false
    }
  }, [])

  async function verComprobante(id) {
    setError('')
    try {
      await abrirComprobante(id)
    } catch (e) {
      setError(e.message)
    }
  }

  async function alCorregir(correccion) {
    setCorrigiendo(null)
    setError('')
    setAviso(
      `Registraste la corrección en ${formatearDominio(correccion.dominio)}. ` +
        'El registro original se conserva y quedó vinculado.',
    )
    window.scrollTo({ top: 0 })
    try {
      setRegistros(await listarRegistros())
    } catch (e) {
      setError(e.message)
    }
  }

  const filtro = normalizarDominio(busqueda)
  const visibles =
    registros?.filter((registro) => registro.dominio.includes(filtro) && ESTADOS[estado].incluye(registro)) ?? []

  return (
    <LayoutPanel enlaces={ENLACES_TALLER}>
      <h1 className="titulo-pagina">Registros realizados</h1>
      <p className="subtitulo-pagina">
        Intervenciones que registraste. No se pueden editar ni eliminar: si hay un error, registrá una corrección
        vinculada.
      </p>

      {aviso && (
        <p className="aviso aviso-exito" role="status">
          <CircleCheck size={18} aria-hidden="true" />
          {aviso}
        </p>
      )}
      {error && (
        <p className="aviso aviso-error" role="alert">
          <CircleAlert size={18} aria-hidden="true" />
          {error}
        </p>
      )}

      {registros === null && !error && <p className="registros-vacio">Cargando registros…</p>}

      {registros?.length === 0 && (
        <div className="registros-vacio">
          <ClipboardList size={32} aria-hidden="true" />
          <p>Todavía no registraste intervenciones.</p>
          <Link className="boton-secundario" to="/taller">
            Registrar una intervención
          </Link>
        </div>
      )}

      {registros?.length > 0 && (
        <>
          <div className="registros-filtros">
            <Campo
              id="busqueda"
              etiqueta="Buscar por dominio"
              className="campo-mono campo-dominio"
              autoComplete="off"
              placeholder="AE123CD"
              value={busqueda}
              onChange={(evento) => setBusqueda(normalizarDominio(evento.target.value).slice(0, 7))}
            />
            <Campo
              id="estado"
              etiqueta="Estado"
              como="select"
              value={estado}
              onChange={(evento) => setEstado(evento.target.value)}
            >
              {Object.entries(ESTADOS).map(([clave, { nombre }]) => (
                <option key={clave} value={clave}>
                  {nombre}
                </option>
              ))}
            </Campo>
          </div>

          {visibles.length === 0 ? (
            <p className="registros-vacio">No hay registros con esos filtros.</p>
          ) : (
            <table className="tabla-registros">
              <thead>
                <tr>
                  <th scope="col">Fecha</th>
                  <th scope="col">Dominio</th>
                  <th scope="col">Intervención</th>
                  <th scope="col">Kilometraje</th>
                  <th scope="col">
                    <span className="visualmente-oculto">Acciones</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {visibles.map((registro) => (
                  <Registro
                    key={registro.id}
                    registro={registro}
                    alVerComprobante={verComprobante}
                    alCorregir={(elegido) => {
                      setAviso('')
                      setCorrigiendo(elegido)
                    }}
                  />
                ))}
              </tbody>
            </table>
          )}
        </>
      )}

      <PanelDeslizable
        abierto={corrigiendo !== null}
        titulo="Registrar corrección vinculada"
        alCerrar={() => setCorrigiendo(null)}
      >
        {corrigiendo && (
          <FormularioCorreccion
            intervencion={corrigiendo}
            alCorregir={alCorregir}
            alCancelar={() => setCorrigiendo(null)}
          />
        )}
      </PanelDeslizable>
    </LayoutPanel>
  )
}

export default RegistrosRealizados
