import { useEffect, useState } from 'react'
import { CircleAlert, CircleCheck, History, KeyRound, Plus, ShieldAlert, ShieldCheck } from 'lucide-react'
import { Link, useNavigate, useParams } from 'react-router'
import { abrirComprobante } from '../../api/intervenciones.js'
import { listarVehiculos, obtenerHistorial, obtenerMetricas } from '../../api/vehiculos.js'
import Badge from '../../components/Badge.jsx'
import LayoutPanel from '../../components/LayoutPanel.jsx'
import PanelDeslizable from '../../components/PanelDeslizable.jsx'
import Patente from '../../components/Patente.jsx'
import SelectorVehiculo from '../../components/SelectorVehiculo.jsx'
import FormularioCorreccion from '../../components/historial/FormularioCorreccion.jsx'
import LineaDeTiempo from '../../components/historial/LineaDeTiempo.jsx'
import MetricasVehiculo from '../../components/historial/MetricasVehiculo.jsx'
import { formatearDominio } from '../../utils/dominio.js'
import { ENLACES_PROPIETARIO } from './navegacion.js'
import '../../components/formulario.css'
import './Historial.css'

// El historial y sus métricas se piden juntos: las dos vistas tienen que mostrar los mismos registros.
async function cargarHistorial(vehiculoId) {
  const [historial, metricas] = await Promise.all([obtenerHistorial(vehiculoId), obtenerMetricas(vehiculoId)])
  return { ...historial, metricas }
}

function EncabezadoVehiculo({ vehiculo, integridadVerificada }) {
  return (
    <section className="historial-vehiculo" aria-labelledby="titulo-vehiculo">
      <Patente dominio={vehiculo.dominio} />
      <div className="historial-vehiculo-datos">
        <h1 id="titulo-vehiculo">
          {vehiculo.marca} {vehiculo.modelo}
        </h1>
        <div className="historial-vehiculo-detalle">
          <span>Modelo {vehiculo.anio}</span>
          {integridadVerificada ? (
            <Badge tipo="exito" Icono={ShieldCheck}>
              Integridad verificada
            </Badge>
          ) : (
            <Badge tipo="error" Icono={ShieldAlert}>
              Integridad no verificada
            </Badge>
          )}
        </div>
      </div>
      <div className="historial-vehiculo-acciones">
        <Link className="boton-secundario" to={`/propietario/codigo?vehiculo=${vehiculo.id}`}>
          <KeyRound size={18} aria-hidden="true" />
          <span className="texto-escritorio">Generar código</span>
          <span className="texto-movil">Código</span>
        </Link>
        <Link className="boton-primario boton-ajustado" to={`/propietario/intervencion?vehiculo=${vehiculo.id}`}>
          <Plus size={18} aria-hidden="true" />
          <span className="texto-escritorio">Registrar intervención propia</span>
          <span className="texto-movil">Intervención</span>
        </Link>
      </div>
    </section>
  )
}

// Historial completo de un vehículo del propietario, del más reciente al más antiguo (HU-012).
function Historial() {
  const { vehiculoId } = useParams()
  const navigate = useNavigate()
  const [vehiculos, setVehiculos] = useState([])
  // Datos o error del último vehículo pedido: mientras llega otro, no se muestra el anterior.
  const [historial, setHistorial] = useState({ vehiculoId: null, datos: null, error: '' })
  const [errorAccion, setErrorAccion] = useState('')
  const [aviso, setAviso] = useState({ vehiculoId: null, texto: '' })
  const [corrigiendo, setCorrigiendo] = useState(null)

  useEffect(() => {
    let vigente = true
    listarVehiculos()
      .then((lista) => vigente && setVehiculos(lista))
      .catch(() => {}) // sin la lista solo falta el selector; el historial informa sus propios errores
    return () => {
      vigente = false
    }
  }, [])

  useEffect(() => {
    let vigente = true
    cargarHistorial(vehiculoId)
      .then((datos) => vigente && setHistorial({ vehiculoId, datos, error: '' }))
      .catch((e) => vigente && setHistorial({ vehiculoId, datos: null, error: e.message }))
    return () => {
      vigente = false
    }
  }, [vehiculoId])

  async function verComprobante(id) {
    setErrorAccion('')
    try {
      await abrirComprobante(id)
    } catch (e) {
      setErrorAccion(e.message)
    }
  }

  async function alCorregir() {
    setCorrigiendo(null)
    setErrorAccion('')
    setAviso({ vehiculoId, texto: 'Registraste la corrección. El registro original se conserva y quedó vinculado.' })
    window.scrollTo({ top: 0 })
    try {
      setHistorial({ vehiculoId, datos: await cargarHistorial(vehiculoId), error: '' })
    } catch (e) {
      setErrorAccion(e.message)
    }
  }

  // El propietario corrige solo sus autorreportadas, y la versión vigente (no una ya corregida).
  const puedeCorregir = (intervencion) => intervencion.origen === 'propietario' && !intervencion.corregido_por

  const actual = historial.vehiculoId === vehiculoId
  const datos = actual ? historial.datos : null
  const error = (actual && historial.error) || errorAccion
  const dominio = datos?.vehiculo.dominio ?? vehiculos.find((v) => v.id === vehiculoId)?.dominio

  return (
    <LayoutPanel enlaces={ENLACES_PROPIETARIO}>
      <nav className="migas" aria-label="Ubicación">
        <Link to="/propietario">Mis vehículos</Link>
        <span aria-hidden="true">/</span>
        <span aria-current="page">{dominio ? formatearDominio(dominio) : 'Historial'}</span>
      </nav>

      {vehiculos.length > 1 && (
        <div className="historial-selector">
          <SelectorVehiculo
            vehiculos={vehiculos}
            seleccionado={vehiculoId}
            alSeleccionar={(id) => navigate(`/propietario/vehiculos/${id}`)}
          />
        </div>
      )}

      {aviso.vehiculoId === vehiculoId && aviso.texto && (
        <p className="aviso aviso-exito" role="status">
          <CircleCheck size={18} aria-hidden="true" />
          {aviso.texto}
        </p>
      )}
      {error && (
        <p className="aviso aviso-error" role="alert">
          <CircleAlert size={18} aria-hidden="true" />
          {error}
        </p>
      )}

      {datos === null ? (
        !error && <p className="historial-cargando">Cargando historial…</p>
      ) : (
        <>
          <EncabezadoVehiculo vehiculo={datos.vehiculo} integridadVerificada={datos.integridad_verificada} />

          {!datos.integridad_verificada && (
            <p className="aviso aviso-error" role="alert">
              <ShieldAlert size={18} aria-hidden="true" />
              Algún registro de este historial no coincide con su cadena de verificación: pudo haber sido alterado
              fuera del sistema.
            </p>
          )}

          {datos.metricas.servicios > 0 && <MetricasVehiculo metricas={datos.metricas} />}

          <section className="historial" aria-labelledby="titulo-historial">
            <div className="historial-titulo">
              <h2 id="titulo-historial">Historial de intervenciones</h2>
              {datos.intervenciones.length > 1 && <span>Del más reciente al más antiguo</span>}
            </div>
            {datos.intervenciones.length === 0 ? (
              <div className="historial-vacio">
                <History size={32} aria-hidden="true" />
                <p>Aún no se registran intervenciones para este vehículo.</p>
                <span>
                  Generá un código para que un taller cargue el próximo servicio, o registrá uno que hayas hecho
                  vos.
                </span>
              </div>
            ) : (
              <LineaDeTiempo
                intervenciones={datos.intervenciones}
                alVerComprobante={verComprobante}
                puedeCorregir={puedeCorregir}
                alCorregir={(intervencion) => {
                  setAviso({ vehiculoId: null, texto: '' })
                  setCorrigiendo(intervencion)
                }}
              />
            )}
          </section>
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

export default Historial
