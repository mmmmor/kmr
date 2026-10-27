import { useEffect, useState } from 'react'
import { CircleAlert, ClipboardList, FileText } from 'lucide-react'
import { Link } from 'react-router'
import { abrirComprobante } from '../../api/intervenciones.js'
import { listarRegistros } from '../../api/taller.js'
import Campo from '../../components/Campo.jsx'
import LayoutPanel from '../../components/LayoutPanel.jsx'
import Patente from '../../components/Patente.jsx'
import { normalizarDominio } from '../../utils/dominio.js'
import { formatearFecha } from '../../utils/fechas.js'
import { formatearMiles } from '../../utils/intervenciones.js'
import { ENLACES_TALLER } from './navegacion.js'
import '../../components/formulario.css'
import './RegistrosRealizados.css'

// Intervenciones registradas por el taller, de la más reciente a la más antigua.
function RegistrosRealizados() {
  const [registros, setRegistros] = useState(null)
  const [error, setError] = useState('')
  const [busqueda, setBusqueda] = useState('')

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

  const filtro = normalizarDominio(busqueda)
  const visibles = registros?.filter((registro) => registro.dominio.includes(filtro)) ?? []

  return (
    <LayoutPanel enlaces={ENLACES_TALLER}>
      <h1 className="titulo-pagina">Registros realizados</h1>
      <p className="subtitulo-pagina">Intervenciones que registraste. No se pueden editar ni eliminar.</p>

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
          </div>

          {visibles.length === 0 ? (
            <p className="registros-vacio">No hay registros para ese dominio.</p>
          ) : (
            <table className="tabla-registros">
              <thead>
                <tr>
                  <th scope="col">Fecha</th>
                  <th scope="col">Dominio</th>
                  <th scope="col">Intervención</th>
                  <th scope="col">Kilometraje</th>
                  <th scope="col">
                    <span className="visualmente-oculto">Comprobante</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {visibles.map((registro) => (
                  <tr key={registro.id}>
                    <td className="tabla-registros-fecha mono">{formatearFecha(registro.fecha_intervencion)}</td>
                    <td className="tabla-registros-dominio">
                      <Patente dominio={registro.dominio} tamano="chico" />
                    </td>
                    <td className="tabla-registros-intervencion">
                      <strong>{registro.tipo}</strong>
                      {registro.descripcion && <span>{registro.descripcion}</span>}
                    </td>
                    <td className="tabla-registros-km mono">{formatearMiles(registro.kilometraje)} km</td>
                    <td className="tabla-registros-comprobante">
                      {registro.tiene_comprobante && (
                        <button type="button" className="boton-texto" onClick={() => verComprobante(registro.id)}>
                          <FileText size={16} aria-hidden="true" />
                          Ver comprobante
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </>
      )}
    </LayoutPanel>
  )
}

export default RegistrosRealizados
