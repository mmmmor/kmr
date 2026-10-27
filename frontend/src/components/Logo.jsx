import { Gauge } from 'lucide-react'
import { Link } from 'react-router'
import './Logo.css'

function Logo({ invertido = false }) {
  return (
    <Link to="/" className={`logo ${invertido ? 'logo-invertido' : ''}`}>
      <span className="logo-icono">
        <Gauge size={20} strokeWidth={2.2} aria-hidden="true" />
      </span>
      <span className="logo-texto">
        Km<span className="logo-r">R</span>
      </span>
    </Link>
  )
}

export default Logo
