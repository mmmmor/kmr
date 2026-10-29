import { Gauge, KeyRound, ShieldCheck } from 'lucide-react'
import BuscadorDominio from '../../components/BuscadorDominio.jsx'
import LayoutPublico from '../../components/LayoutPublico.jsx'
import Patente from '../../components/Patente.jsx'
import './Inicio.css'

const TARJETAS = [
  {
    Icono: ShieldCheck,
    titulo: 'Registros que no se modifican',
    texto:
      'Cada servicio queda asentado de forma permanente. Las correcciones se agregan vinculadas al registro ' +
      'original, que se conserva.',
  },
  {
    Icono: Gauge,
    titulo: 'Kilometraje contrastado',
    texto:
      'Cada carga se compara con los registros anteriores del vehículo y las inconsistencias quedan señaladas ' +
      'a la vista.',
  },
  {
    Icono: KeyRound,
    titulo: 'Carga autorizada por el dueño',
    texto:
      'Un taller solo puede registrar un servicio con el código de seis dígitos que le entrega el propietario ' +
      'del vehículo.',
  },
]

// Inicio público con el buscador de la consulta por dominio (HU-010).
function Inicio() {
  return (
    <LayoutPublico>
      <section className="inicio-portada" aria-labelledby="inicio-titulo">
        <span className="inicio-sello">
          <ShieldCheck size={16} aria-hidden="true" />
          Historial de mantenimiento vehicular
        </span>
        <h1 id="inicio-titulo">Conocé el mantenimiento real de un auto antes de comprarlo</h1>
        <p className="inicio-bajada">
          Ingresá el dominio y consultá los servicios registrados por talleres verificados y por su propietario. Sin
          datos personales del titular.
        </p>
        <BuscadorDominio />
        <p className="inicio-formatos">
          <span>Formatos admitidos:</span>
          <Patente dominio="AA123BB" tamano="chico" />
          <span>o</span>
          <Patente dominio="ABC123" tamano="chico" />
          <span>· La consulta es gratuita y no requiere cuenta.</span>
        </p>
      </section>

      <section id="como-funciona" className="inicio-tarjetas" aria-label="Cómo funciona">
        {TARJETAS.map(({ Icono, titulo, texto }) => (
          <article key={titulo} className="inicio-tarjeta">
            <span className="inicio-tarjeta-icono">
              <Icono size={20} aria-hidden="true" />
            </span>
            <h2>{titulo}</h2>
            <p>{texto}</p>
          </article>
        ))}
      </section>
    </LayoutPublico>
  )
}

export default Inicio
