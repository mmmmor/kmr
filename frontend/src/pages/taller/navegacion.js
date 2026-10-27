import { ClipboardList, Search, Wrench } from 'lucide-react'

// Secciones de la barra lateral del taller.
export const ENLACES_TALLER = [
  { a: '/taller', texto: 'Registrar intervención', Icono: Wrench },
  { a: '/taller/registros', texto: 'Registros realizados', Icono: ClipboardList },
  { a: '/', texto: 'Consulta pública', Icono: Search },
]
