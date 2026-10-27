import { useState } from 'react'
import { ChevronRight, CircleAlert, Clock, KeyRound, User } from 'lucide-react'
import { autorizar } from '../../api/taller.js'
import Campo from '../../components/Campo.jsx'
import ComoFunciona from '../../components/ComoFunciona.jsx'
import Patente from '../../components/Patente.jsx'
import { formatoDominio, normalizarDominio } from '../../utils/dominio.js'

const PASOS_AUTORIZACION = [
  { Icono: User, texto: 'El propietario genera el código desde su cuenta y te lo comparte.' },
  { Icono: KeyRound, texto: 'Lo ingresás acá junto con el dominio del vehículo.' },
  { Icono: Clock, texto: 'Vale por 24 horas y para una sola intervención.' },
]

// Paso 1: dominio + código. Si el código venció mientras se cargaban los datos, se vuelve acá
// con el dominio ya escrito y el error en el código (`errorCodigo`).
function PasoAutorizacion({ dominioInicial = '', errorCodigo = '', alAutorizar }) {
  const [dominio, setDominio] = useState(dominioInicial)
  const [codigo, setCodigo] = useState('')
  const [errores, setErrores] = useState(errorCodigo ? { codigo: errorCodigo } : {})
  const [errorGeneral, setErrorGeneral] = useState('')
  const [enviando, setEnviando] = useState(false)

  async function enviar(evento) {
    evento.preventDefault()
    setErrorGeneral('')

    const faltantes = {}
    if (!dominio) faltantes.dominio = 'Completá este campo.'
    if (!codigo) faltantes.codigo = 'Completá este campo.'
    else if (codigo.length < 6) faltantes.codigo = 'El código tiene 6 dígitos.'
    if (Object.keys(faltantes).length > 0) {
      setErrores(faltantes)
      return
    }

    setEnviando(true)
    try {
      const vehiculo = await autorizar({ dominio, codigo })
      alAutorizar({ codigo, vehiculo })
    } catch (error) {
      const campos = error.campos ?? {}
      setErrores(campos)
      if (Object.keys(campos).length === 0) setErrorGeneral(error.message)
      setEnviando(false)
    }
  }

  return (
    <div className="taller-grilla">
      <form className="tarjeta-taller" onSubmit={enviar} noValidate>
        {errorGeneral && (
          <p className="aviso aviso-error" role="alert">
            <CircleAlert size={18} aria-hidden="true" />
            {errorGeneral}
          </p>
        )}
        <Campo
          id="dominio"
          etiqueta="Dominio"
          className="campo-mono campo-dominio"
          autoComplete="off"
          autoCapitalize="characters"
          spellCheck={false}
          placeholder="AA123BB"
          value={dominio}
          onChange={(evento) => {
            setDominio(normalizarDominio(evento.target.value).slice(0, 7))
            setErrores((anteriores) => ({ ...anteriores, dominio: undefined }))
          }}
          error={errores.dominio}
          autoFocus={!dominioInicial}
        />
        {formatoDominio(dominio) && (
          <div className="vista-patente">
            <Patente dominio={dominio} tamano="grande" />
          </div>
        )}
        <Campo
          id="codigo"
          etiqueta="Código de autorización"
          className="campo-codigo"
          inputMode="numeric"
          autoComplete="one-time-code"
          placeholder="000000"
          value={codigo}
          onChange={(evento) => {
            setCodigo(evento.target.value.replace(/\D/g, '').slice(0, 6))
            setErrores((anteriores) => ({ ...anteriores, codigo: undefined }))
          }}
          error={errores.codigo}
          ayuda="Seis dígitos. Pedíselo al propietario: lo genera desde su cuenta."
          autoFocus={Boolean(dominioInicial)}
        />
        <button type="submit" className="boton-primario boton-con-icono" disabled={enviando}>
          {enviando ? 'Validando…' : 'Validar y continuar'}
          {!enviando && <ChevronRight size={20} aria-hidden="true" />}
        </button>
      </form>

      <ComoFunciona titulo="Cómo funciona la autorización" items={PASOS_AUTORIZACION} />
    </div>
  )
}

export default PasoAutorizacion
