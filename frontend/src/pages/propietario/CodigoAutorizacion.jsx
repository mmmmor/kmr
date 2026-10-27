import { useEffect, useState } from 'react'
import {
  CalendarDays,
  Check,
  CircleAlert,
  CircleX,
  Clock,
  Copy,
  KeyRound,
  Lock,
  RotateCw,
  Wrench,
} from 'lucide-react'
import { Link, useSearchParams } from 'react-router'
import { generarCodigo, listarCodigos, listarVehiculos } from '../../api/vehiculos.js'
import Badge from '../../components/Badge.jsx'
import ComoFunciona from '../../components/ComoFunciona.jsx'
import LayoutPanel from '../../components/LayoutPanel.jsx'
import SelectorVehiculo from '../../components/SelectorVehiculo.jsx'
import { useAhora } from '../../hooks/useAhora.js'
import { formatearFecha, formatearFechaHora, formatearHora, tiempoRestante } from '../../utils/fechas.js'
import { ENLACES_PROPIETARIO } from './navegacion.js'
import '../../components/formulario.css'
import './CodigoAutorizacion.css'

const REGLAS = [
  { Icono: Clock, texto: 'Vale por 24 horas desde que lo generás.' },
  { Icono: Wrench, texto: 'Autoriza una sola intervención: cuando el taller la registra, el código se consume.' },
  { Icono: RotateCw, texto: 'Si generás uno nuevo, el anterior deja de funcionar.' },
  { Icono: Lock, texto: 'Después de 5 intentos fallidos se invalida por seguridad.' },
]

const ESTADOS = {
  vigente: { texto: 'Vigente', tipo: 'exito', Icono: Check },
  utilizado: { texto: 'Utilizado', tipo: 'exito', Icono: Check },
  vencido: { texto: 'Vencido', tipo: 'neutro', Icono: Clock },
  invalidado: { texto: 'Invalidado', tipo: 'error', Icono: CircleX },
}

function EstadoCodigo({ estado }) {
  const { texto, tipo, Icono } = ESTADOS[estado]
  return (
    <Badge tipo={tipo} Icono={Icono}>
      {texto}
    </Badge>
  )
}

// "482915" → "482 915"
function separar(codigo) {
  return `${codigo.slice(0, 3)} ${codigo.slice(3)}`
}

function detalle(codigo, maxIntentos) {
  if (codigo.estado === 'utilizado') {
    return `Usado por ${codigo.taller ?? 'un taller'} el ${formatearFecha(codigo.fecha_uso)} a las ${formatearHora(codigo.fecha_uso)}`
  }
  if (codigo.estado === 'vencido') return 'No se usó dentro de las 24 horas'
  if (codigo.intentos_fallidos > maxIntentos) return `Se superaron los ${maxIntentos} intentos fallidos`
  return 'Se reemplazó por un código nuevo'
}

function CodigoVigente({ codigo, maxIntentos, ahora, generando, alGenerar }) {
  const [copiado, setCopiado] = useState(false)

  async function copiar() {
    try {
      await navigator.clipboard.writeText(codigo.codigo)
      setCopiado(true)
      setTimeout(() => setCopiado(false), 2000)
    } catch {
      // Sin permiso de portapapeles: el código igual queda a la vista para copiarlo a mano.
    }
  }

  return (
    <section className="tarjeta-codigo" aria-labelledby="titulo-vigente">
      <header className="tarjeta-codigo-encabezado">
        <h2 id="titulo-vigente">Código vigente</h2>
        <div className="tarjeta-codigo-etiquetas">
          <EstadoCodigo estado="vigente" />
          <Badge>Un solo uso</Badge>
        </div>
      </header>

      <div className="digitos" aria-hidden="true">
        {codigo.codigo.split('').map((digito, i) => (
          <span key={i}>{digito}</span>
        ))}
      </div>
      <p className="visualmente-oculto">Código: {codigo.codigo.split('').join(' ')}</p>

      <ul className="codigo-datos">
        <li>
          <Clock size={18} aria-hidden="true" />
          <span>
            Vence el {formatearFechaHora(codigo.fecha_vencimiento)}{' '}
            <span className="sin-corte">(en {tiempoRestante(codigo.fecha_vencimiento, ahora)}).</span>
          </span>
        </li>
        <li>
          <CalendarDays size={18} aria-hidden="true" />
          Generado el {formatearFechaHora(codigo.fecha_generacion)}.
        </li>
        <li>
          <Lock size={18} aria-hidden="true" />
          Intentos fallidos: {codigo.intentos_fallidos} de {maxIntentos}.
        </li>
      </ul>

      <div className="tarjeta-codigo-acciones">
        <button type="button" className="boton-primario boton-ajustado" onClick={copiar}>
          {copiado ? <Check size={18} aria-hidden="true" /> : <Copy size={18} aria-hidden="true" />}
          {copiado ? 'Código copiado' : 'Copiar código'}
        </button>
        <button type="button" className="boton-secundario" onClick={alGenerar} disabled={generando}>
          <RotateCw size={18} aria-hidden="true" />
          {generando ? 'Generando…' : 'Generar nuevo código'}
        </button>
      </div>
      <p className="tarjeta-codigo-nota">Al generar uno nuevo, este código deja de funcionar.</p>
    </section>
  )
}

function SinCodigo({ generando, alGenerar }) {
  return (
    <section className="tarjeta-codigo" aria-labelledby="titulo-vigente">
      <h2 id="titulo-vigente">Código vigente</h2>
      <p className="tarjeta-codigo-vacia">
        No hay un código vigente para este vehículo. Generá uno cuando vayas a llevarlo al taller y
        compartilo con quien va a hacer el servicio.
      </p>
      <button type="button" className="boton-primario boton-ajustado" onClick={alGenerar} disabled={generando}>
        <KeyRound size={18} aria-hidden="true" />
        {generando ? 'Generando…' : 'Generar código'}
      </button>
    </section>
  )
}

function CodigosAnteriores({ codigos, maxIntentos }) {
  return (
    <section className="codigos-anteriores" aria-labelledby="titulo-anteriores">
      <h2 id="titulo-anteriores">Códigos anteriores</h2>
      {codigos.length === 0 ? (
        <p className="codigos-anteriores-vacio">Todavía no hay códigos anteriores.</p>
      ) : (
        <table className="tabla-codigos">
          <thead>
            <tr>
              <th scope="col">Código</th>
              <th scope="col">Generado</th>
              <th scope="col">Estado</th>
              <th scope="col">Detalle</th>
            </tr>
          </thead>
          <tbody>
            {codigos.map((codigo) => (
              <tr key={codigo.id}>
                <td className="tabla-codigos-codigo mono">{separar(codigo.codigo)}</td>
                <td className="tabla-codigos-generado">
                  <span className="solo-movil">Generado el </span>
                  {formatearFechaHora(codigo.fecha_generacion)}
                </td>
                <td className="tabla-codigos-estado">
                  <EstadoCodigo estado={codigo.estado} />
                </td>
                <td className="tabla-codigos-detalle">{detalle(codigo, maxIntentos)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  )
}

// Generación del código temporal que habilita a un taller a registrar una intervención (HU-006).
function CodigoAutorizacion() {
  const [parametros, setParametros] = useSearchParams()
  const [vehiculos, setVehiculos] = useState(null)
  const [codigos, setCodigos] = useState({ vehiculoId: null, datos: null })
  const [error, setError] = useState('')
  const [generando, setGenerando] = useState(false)
  const ahora = useAhora()

  useEffect(() => {
    let vigente = true
    listarVehiculos()
      .then((lista) => vigente && setVehiculos(lista))
      .catch((e) => vigente && setError(e.message))
    return () => {
      vigente = false
    }
  }, [])

  // El vehículo puede venir en la URL (desde "Generar código" de Mis vehículos); si no, el primero.
  const pedido = parametros.get('vehiculo')
  const vehiculoId = vehiculos?.some((v) => v.id === pedido) ? pedido : vehiculos?.[0]?.id

  useEffect(() => {
    if (!vehiculoId) return
    let vigente = true
    listarCodigos(vehiculoId)
      .then((datos) => vigente && setCodigos({ vehiculoId, datos }))
      .catch((e) => vigente && setError(e.message))
    return () => {
      vigente = false
    }
  }, [vehiculoId])

  async function generar() {
    setGenerando(true)
    setError('')
    try {
      await generarCodigo(vehiculoId)
      setCodigos({ vehiculoId, datos: await listarCodigos(vehiculoId) })
    } catch (e) {
      setError(e.message)
    } finally {
      setGenerando(false)
    }
  }

  const datos = codigos.vehiculoId === vehiculoId ? codigos.datos : null
  // Si vence mientras se mira la pantalla, pasa a los anteriores sin volver a pedirlo.
  const vencioRecien = datos?.vigente && new Date(datos.vigente.fecha_vencimiento) <= ahora
  const vigente = vencioRecien ? null : datos?.vigente
  const anteriores = vencioRecien ? [{ ...datos.vigente, estado: 'vencido' }, ...datos.anteriores] : datos?.anteriores

  return (
    <LayoutPanel enlaces={ENLACES_PROPIETARIO}>
      <h1 className="titulo-pagina">Código de autorización</h1>
      <p className="subtitulo-pagina">
        Generá un código para que un taller pueda registrar una intervención en tu vehículo.
      </p>

      {error && (
        <p className="aviso aviso-error" role="alert">
          <CircleAlert size={18} aria-hidden="true" />
          {error}
        </p>
      )}

      {vehiculos?.length === 0 && (
        <div className="codigo-sin-vehiculos">
          <p>Para generar un código, primero vinculá un vehículo a tu cuenta.</p>
          <Link className="boton-secundario" to="/propietario">
            Ir a Mis vehículos
          </Link>
        </div>
      )}

      {vehiculos?.length > 0 && (
        <div className="codigo-grilla">
          <SelectorVehiculo
            vehiculos={vehiculos}
            seleccionado={vehiculoId}
            alSeleccionar={(id) => setParametros({ vehiculo: id }, { replace: true })}
          />
          {datos ? (
            <>
              {vigente ? (
                <CodigoVigente
                  codigo={vigente}
                  maxIntentos={datos.max_intentos_fallidos}
                  ahora={ahora}
                  generando={generando}
                  alGenerar={generar}
                />
              ) : (
                <SinCodigo generando={generando} alGenerar={generar} />
              )}
              <CodigosAnteriores codigos={anteriores} maxIntentos={datos.max_intentos_fallidos} />
            </>
          ) : (
            !error && <p className="codigo-cargando">Cargando códigos…</p>
          )}
          <ComoFunciona
            className="codigo-reglas"
            titulo="Cómo funciona"
            items={REGLAS}
            pie="Compartilo solo con el taller que va a realizar el servicio."
          />
        </div>
      )}
    </LayoutPanel>
  )
}

export default CodigoAutorizacion
