import { Route, Routes } from 'react-router'
import RutaProtegida from './auth/RutaProtegida.jsx'
import Solicitudes from './pages/admin/Solicitudes.jsx'
import InicioPropietario from './pages/propietario/Inicio.jsx'
import Inicio from './pages/publico/Inicio.jsx'
import Login from './pages/publico/Login.jsx'
import RecuperarContrasena from './pages/publico/RecuperarContrasena.jsx'
import Registro from './pages/publico/Registro.jsx'
import InicioTaller from './pages/taller/Inicio.jsx'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Inicio />} />
      <Route path="/registro" element={<Registro />} />
      <Route path="/login" element={<Login />} />
      <Route path="/recuperar" element={<RecuperarContrasena />} />

      <Route element={<RutaProtegida rol="propietario" />}>
        <Route path="/propietario" element={<InicioPropietario />} />
      </Route>
      <Route element={<RutaProtegida rol="taller" />}>
        <Route path="/taller" element={<InicioTaller />} />
      </Route>
      <Route element={<RutaProtegida rol="administrador" />}>
        <Route path="/admin" element={<Solicitudes />} />
      </Route>
    </Routes>
  )
}

export default App
