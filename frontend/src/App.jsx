import { Route, Routes } from 'react-router'
import Inicio from './pages/publico/Inicio.jsx'
import Login from './pages/publico/Login.jsx'
import Registro from './pages/publico/Registro.jsx'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Inicio />} />
      <Route path="/registro" element={<Registro />} />
      <Route path="/login" element={<Login />} />
    </Routes>
  )
}

export default App
