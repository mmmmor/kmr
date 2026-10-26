import { useEffect, useState } from 'react'
import { obtenerSalud } from '../../api/cliente.js'

const ESTADOS = {
  cargando: { texto: 'Consultando la API…', clase: '' },
  ok: { texto: 'API y base de datos conectadas', clase: 'estado-ok' },
  sinBase: {
    texto: 'La API responde, pero no hay conexión con la base de datos',
    clase: 'estado-alerta',
  },
  sinApi: { texto: 'No se pudo conectar con la API', clase: 'estado-alerta' },
}

// Página provisoria: muestra que el frontend llega a la API y la API a MongoDB.
function Inicio() {
  const [estado, setEstado] = useState('cargando')

  useEffect(() => {
    obtenerSalud()
      .then((salud) => setEstado(salud.base_de_datos === 'ok' ? 'ok' : 'sinBase'))
      .catch(() => setEstado('sinApi'))
  }, [])

  const { texto, clase } = ESTADOS[estado]

  return (
    <main className="inicio">
      <h1>KmR</h1>
      <p>Historial de mantenimiento vehicular verificado. Sitio en construcción.</p>
      <p className={`estado ${clase}`}>{texto}</p>
    </main>
  )
}

export default Inicio
