import { Route, Routes } from 'react-router'
import Inicio from './pages/publico/Inicio.jsx'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Inicio />} />
    </Routes>
  )
}

export default App
