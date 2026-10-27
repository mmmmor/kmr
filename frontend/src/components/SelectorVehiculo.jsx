import Patente from './Patente.jsx'
import './SelectorVehiculo.css'

// Tarjetas para elegir uno de los vehículos del propietario (funcionan como radios).
function SelectorVehiculo({ vehiculos, seleccionado, alSeleccionar, etiqueta }) {
  return (
    <fieldset className="selector-vehiculo">
      <legend className={etiqueta ? 'selector-vehiculo-etiqueta' : 'visualmente-oculto'}>
        {etiqueta ?? 'Vehículo'}
      </legend>
      <div className="selector-vehiculo-opciones">
        {vehiculos.map((vehiculo) => (
          <label
            key={vehiculo.id}
            className={`selector-vehiculo-opcion ${vehiculo.id === seleccionado ? 'activa' : ''}`}
          >
            <input
              type="radio"
              name="vehiculo"
              value={vehiculo.id}
              checked={vehiculo.id === seleccionado}
              onChange={() => alSeleccionar(vehiculo.id)}
            />
            <Patente dominio={vehiculo.dominio} tamano="chico" />
            <span className="selector-vehiculo-texto">
              <strong>
                {vehiculo.marca} {vehiculo.modelo}
              </strong>
              <span>Modelo {vehiculo.anio}</span>
            </span>
          </label>
        ))}
      </div>
    </fieldset>
  )
}

export default SelectorVehiculo
