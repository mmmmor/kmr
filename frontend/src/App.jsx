import { Route, Routes } from 'react-router'
import RutaProtegida from './auth/RutaProtegida.jsx'
import Solicitudes from './pages/admin/Solicitudes.jsx'
import CodigoAutorizacion from './pages/propietario/CodigoAutorizacion.jsx'
import MisVehiculos from './pages/propietario/MisVehiculos.jsx'
import Inicio from './pages/publico/Inicio.jsx'
import Login from './pages/publico/Login.jsx'
import RecuperarContrasena from './pages/publico/RecuperarContrasena.jsx'
import Registro from './pages/publico/Registro.jsx'
import RegistrarIntervencion from './pages/taller/RegistrarIntervencion.jsx'
import RegistrosRealizados from './pages/taller/RegistrosRealizados.jsx'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Inicio />} />
      <Route path="/registro" element={<Registro />} />
      <Route path="/login" element={<Login />} />
      <Route path="/recuperar" element={<RecuperarContrasena />} />

      <Route element={<RutaProtegida rol="propietario" />}>
        <Route path="/propietario" element={<MisVehiculos />} />
        <Route path="/propietario/codigo" element={<CodigoAutorizacion />} />
      </Route>
      <Route element={<RutaProtegida rol="taller" />}>
        <Route path="/taller" element={<RegistrarIntervencion />} />
        <Route path="/taller/registros" element={<RegistrosRealizados />} />
      </Route>
      <Route element={<RutaProtegida rol="administrador" />}>
        <Route path="/admin" element={<Solicitudes />} />
      </Route>
    </Routes>
  )
}

export default App
