import { useEffect, useState } from 'react'
import { CircleAlert, CircleCheck, KeyRound, Plus } from 'lucide-react'
import { Link } from 'react-router'
import { listarVehiculos } from '../../api/vehiculos.js'
import LayoutPanel from '../../components/LayoutPanel.jsx'
import PanelDeslizable from '../../components/PanelDeslizable.jsx'
import Patente from '../../components/Patente.jsx'
import { formatearDominio } from '../../utils/dominio.js'
import { ENLACES_PROPIETARIO } from './navegacion.js'
import VincularVehiculo from './VincularVehiculo.jsx'
import '../../components/formulario.css'
import './MisVehiculos.css'

function TarjetaVehiculo({ vehiculo }) {
  return (
    <article className="vehiculo">
      <div className="vehiculo-encabezado">
        <Patente dominio={vehiculo.dominio} />
        <div>
          <h2>
            {vehiculo.marca} {vehiculo.modelo}
          </h2>
          <p>Modelo {vehiculo.anio}</p>
        </div>
      </div>
      <p className="vehiculo-sin-registros">Todavía no hay intervenciones registradas.</p>
      <div className="vehiculo-acciones">
        <Link className="boton-secundario" to={`/propietario/codigo?vehiculo=${vehiculo.id}`}>
          <KeyRound size={18} aria-hidden="true" />
          Generar código
        </Link>
      </div>
    </article>
  )
}

// Vehículos vinculados a la cuenta y alta de uno nuevo (HU-005).
function MisVehiculos() {
  const [vehiculos, setVehiculos] = useState(null)
  const [errorCarga, setErrorCarga] = useState('')
  const [vinculando, setVinculando] = useState(false)
  const [aviso, setAviso] = useState('')

  useEffect(() => {
    let vigente = true
    listarVehiculos()
      .then((lista) => vigente && setVehiculos(lista))
      .catch((error) => vigente && setErrorCarga(error.message))
    return () => {
      vigente = false
    }
  }, [])

  function alVincular(vehiculo) {
    setVinculando(false)
    setVehiculos((anteriores) => [...anteriores, vehiculo])
    setAviso(`Vinculaste el vehículo ${formatearDominio(vehiculo.dominio)}.`)
  }

  return (
    <LayoutPanel enlaces={ENLACES_PROPIETARIO}>
      <h1 className="titulo-pagina">Mis vehículos</h1>
      <p className="subtitulo-pagina">Vehículos vinculados a tu cuenta.</p>

      {aviso && (
        <p className="aviso aviso-exito" role="status">
          <CircleCheck size={18} aria-hidden="true" />
          {aviso}
        </p>
      )}
      {errorCarga && (
        <p className="aviso aviso-error" role="alert">
          <CircleAlert size={18} aria-hidden="true" />
          {errorCarga}
        </p>
      )}

      {vehiculos === null ? (
        !errorCarga && <p className="vehiculos-cargando">Cargando vehículos…</p>
      ) : (
        <div className="vehiculos">
          {vehiculos.map((vehiculo) => (
            <TarjetaVehiculo key={vehiculo.id} vehiculo={vehiculo} />
          ))}
          <button
            type="button"
            className="vehiculo-nuevo"
            onClick={() => {
              setAviso('')
              setVinculando(true)
            }}
          >
            <span className="vehiculo-nuevo-icono">
              <Plus size={26} aria-hidden="true" />
            </span>
            <strong>{vehiculos.length > 0 ? 'Vincular otro vehículo' : 'Vincular un vehículo'}</strong>
            <span>Ingresá el dominio de un vehículo del que seas titular.</span>
          </button>
        </div>
      )}

      <PanelDeslizable abierto={vinculando} titulo="Vincular vehículo" alCerrar={() => setVinculando(false)}>
        <VincularVehiculo alVincular={alVincular} alCancelar={() => setVinculando(false)} />
      </PanelDeslizable>
    </LayoutPanel>
  )
}

export default MisVehiculos
