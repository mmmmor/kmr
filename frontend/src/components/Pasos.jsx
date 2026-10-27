import { Check } from 'lucide-react'
import './Pasos.css'

// Indicador de pasos de un flujo. En el celular solo se lee el nombre del paso actual.
function Pasos({ pasos, actual }) {
  return (
    <ol className="pasos">
      {pasos.map((texto, i) => {
        const estado = i < actual ? 'completo' : i === actual ? 'actual' : 'pendiente'
        return (
          <li key={texto} className={`paso paso-${estado}`} aria-current={i === actual ? 'step' : undefined}>
            <span className="paso-numero">
              {estado === 'completo' ? <Check size={16} strokeWidth={3} aria-hidden="true" /> : i + 1}
            </span>
            <span className="paso-texto">
              {texto}
              {estado === 'completo' && <span className="visualmente-oculto"> (completo)</span>}
            </span>
          </li>
        )
      })}
    </ol>
  )
}

export default Pasos
