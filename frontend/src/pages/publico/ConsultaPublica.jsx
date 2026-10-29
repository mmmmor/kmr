import { useEffect, useState } from 'react'
import { ChevronLeft, CircleAlert, Lock, SearchX, ShieldAlert, ShieldCheck, TriangleAlert } from 'lucide-react'
import { Link, useParams } from 'react-router'
import { consultarDominio } from '../../api/publico.js'
import Badge from '../../components/Badge.jsx'
import BuscadorDominio from '../../components/BuscadorDominio.jsx'
import LayoutPublico from '../../components/LayoutPublico.jsx'
import Patente from '../../components/Patente.jsx'
import LineaDeTiempo from '../../components/historial/LineaDeTiempo.jsx'
import { formatoDominio, normalizarDominio } from '../../utils/dominio.js'
import { formatearFecha } from '../../utils/fechas.js'
import { formatearMiles } from '../../utils/intervenciones.js'
import '../../components/formulario.css'
import './ConsultaPublica.css'

// Resumen de las alertas de kilometraje para el aviso de arriba del historial.
function resumenInconsistencias(intervenciones) {
  const conAlerta = intervenciones.filter((i) => i.alerta_kilometraje)
  if (conAlerta.length === 0) return null
  if (conAlerta.length > 1) {
    return {
      titulo: `Se registraron ${conAlerta.length} inconsistencias de kilometraje.`,
      texto: 'Están señaladas en el historial. Cuando un registro se corrigió, se conservan los dos.',
      id: conAlerta[0].id,
    }
  }
  const [registro] = conAlerta
  const que =
    registro.alerta_kilometraje.tipo === 'kilometraje_inferior'
      ? 'declara un valor inferior al anterior'
      : 'declara un incremento incompatible con el tiempo transcurrido'
  const correccion = registro.corregido_por
    ? ` y fue corregido por el registro del ${formatearFecha(registro.corregido_por.fecha)}. Ambos registros se conservan.`
    : '.'
  return {
    titulo: 'Se registró una inconsistencia de kilometraje.',
    texto: `El registro del ${formatearFecha(registro.fecha)} ${que}${correccion}`,
    id: registro.id,
  }
}

function Resumen({ consulta }) {
  const { vehiculo, intervenciones, ultima_lectura: ultima, integridad_verificada: integra } = consulta
  const cantidad = intervenciones.length
  return (
    <section className="consulta-resumen" aria-label="Resumen del vehículo">
      <div className="consulta-vehiculo">
        <Patente dominio={vehiculo.dominio} tamano="grande" />
        <div>
          <h1>
            {vehiculo.marca} {vehiculo.modelo}
          </h1>
          <p>Modelo {vehiculo.anio}</p>
        </div>
      </div>
      <dl className="consulta-datos">
        <div>
          <dt>Registros</dt>
          <dd className="mono">{cantidad}</dd>
        </div>
        <div>
          <dt>Último kilometraje</dt>
          <dd className="mono">{formatearMiles(ultima.kilometraje)} km</dd>
        </div>
        <div>
          <dt>Último servicio</dt>
          <dd className="mono">{formatearFecha(ultima.fecha)}</dd>
        </div>
      </dl>
      {integra ? (
        <div className="consulta-integridad">
          <ShieldCheck size={22} aria-hidden="true" />
          <p>
            <strong>Integridad verificada</strong>
            {cantidad === 1
              ? 'El registro conserva el contenido con el que fue cargado.'
              : `Los ${cantidad} registros conservan el contenido con el que fueron cargados.`}
          </p>
        </div>
      ) : (
        <div className="consulta-integridad consulta-integridad-alterada" role="alert">
          <ShieldAlert size={22} aria-hidden="true" />
          <p>
            <strong>Integridad no verificada</strong>
            Algún registro no coincide con su cadena de verificación: pudo haber sido alterado fuera del sistema.
          </p>
        </div>
      )}
    </section>
  )
}

function Lateral() {
  return (
    <aside className="consulta-lateral">
      <section className="consulta-tarjeta" aria-labelledby="como-leer">
        <h2 id="como-leer">Cómo leer este historial</h2>
        <dl className="consulta-referencias">
          <dt>
            <Badge tipo="exito">Taller verificado</Badge>
          </dt>
          <dd>Registro cargado por un taller aprobado, con autorización del propietario.</dd>
          <dt>
            <Badge>Autorreportado</Badge>
          </dt>
          <dd>Registro cargado por el propio dueño. Indica si adjuntó comprobante de los insumos.</dd>
          <dt>
            <Badge tipo="ambar">Inconsistencia</Badge>
          </dt>
          <dd>El kilometraje no es coherente con los registros anteriores.</dd>
          <dt>
            <Badge>Corrección</Badge>
          </dt>
          <dd>Nuevo registro que corrige a otro. El original nunca se modifica ni se elimina.</dd>
        </dl>
      </section>
      <section className="consulta-tarjeta consulta-privacidad">
        <Lock size={20} aria-hidden="true" />
        <div>
          <h2>Sin datos del titular</h2>
          <p>La consulta pública no muestra nombre, documento ni datos de contacto del propietario.</p>
        </div>
      </section>
      <section className="consulta-tarjeta consulta-invitacion">
        <h2>¿Es tu vehículo?</h2>
        <p>Creá una cuenta para vincularlo, autorizar a los talleres y recibir alertas de servicio.</p>
        <Link className="boton-secundario" to="/registro">
          Crear cuenta
        </Link>
      </section>
    </aside>
  )
}

// Resultado de la consulta pública por dominio (HU-010). Sin datos personales del titular.
function ConsultaPublica() {
  const dominio = normalizarDominio(useParams().dominio ?? '')
  const valido = Boolean(formatoDominio(dominio))
  const [consulta, setConsulta] = useState({ dominio: null, datos: null, error: '' })

  useEffect(() => {
    if (!valido) return
    let vigente = true
    consultarDominio(dominio)
      .then((datos) => vigente && setConsulta({ dominio, datos, error: '' }))
      .catch((e) => vigente && setConsulta({ dominio, datos: null, error: e.message }))
    return () => {
      vigente = false
    }
  }, [dominio, valido])

  const actual = consulta.dominio === dominio
  const datos = actual ? consulta.datos : null
  const error = valido ? actual && consulta.error : 'El dominio no es válido: usá el formato AAA 111 o AA 111 AA.'
  const inconsistencias = datos && resumenInconsistencias(datos.intervenciones)

  return (
    <LayoutPublico dominio={dominio}>
      <Link className="consulta-volver" to="/">
        <ChevronLeft size={18} aria-hidden="true" />
        Nueva consulta
      </Link>

      {error && (
        <>
          <p className="aviso aviso-error" role="alert">
            <CircleAlert size={18} aria-hidden="true" />
            {error}
          </p>
          <BuscadorDominio key={dominio} />
        </>
      )}

      {!error && !datos && <p className="consulta-cargando">Consultando el historial…</p>}

      {datos && !datos.vehiculo && (
        <div className="consulta-columnas">
          <section className="consulta-vacia">
            <Patente dominio={dominio} tamano="grande" />
            <SearchX size={28} aria-hidden="true" />
            <p>No se registran intervenciones para el dominio consultado.</p>
          </section>
          <Lateral />
        </div>
      )}

      {datos?.vehiculo && (
        <>
          <Resumen consulta={datos} />
          {inconsistencias && (
            <div className="consulta-inconsistencia" role="note">
              <TriangleAlert size={20} aria-hidden="true" />
              <p>
                <strong>{inconsistencias.titulo}</strong> {inconsistencias.texto}
              </p>
              <a href={`#registro-${inconsistencias.id}`}>Ver registro</a>
            </div>
          )}
          <div className="consulta-columnas">
            <section aria-labelledby="titulo-historial">
              <div className="consulta-titulo">
                <h2 id="titulo-historial">Historial de intervenciones</h2>
                {datos.intervenciones.length > 1 && <span>Del más reciente al más antiguo</span>}
              </div>
              <LineaDeTiempo intervenciones={datos.intervenciones} />
            </section>
            <Lateral />
          </div>
        </>
      )}
    </LayoutPublico>
  )
}

export default ConsultaPublica
