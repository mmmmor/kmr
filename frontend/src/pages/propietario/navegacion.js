import { Car, KeyRound, Search, Wrench } from 'lucide-react'

// Secciones de la barra lateral del propietario.
export const ENLACES_PROPIETARIO = [
  { a: '/propietario', texto: 'Mis vehículos', Icono: Car },
  { a: '/propietario/codigo', texto: 'Código de autorización', Icono: KeyRound },
  { a: '/propietario/intervencion', texto: 'Registrar intervención', Icono: Wrench },
  { a: '/', texto: 'Consulta pública', Icono: Search },
]
