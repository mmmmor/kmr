# KmR

Sistema de trazabilidad y verificación del historial de mantenimiento vehicular. Trabajo Final de Grado de Ingeniería en Software (Universidad Siglo 21).

- **Frontend:** React + Vite.
- **Backend:** Python 3.12 + FastAPI.
- **Base de datos:** MongoDB.

Esta guía explica cómo dejarlo corriendo en Windows, desde cero. Todos los comandos son para **PowerShell**.

## Requisitos

- [Git](https://git-scm.com/downloads)
- [Python 3.12](https://www.python.org/downloads/)
- [Node.js 20.19 o superior](https://nodejs.org/) (recomendado 24 LTS)
- [MongoDB Community Server](https://www.mongodb.com/try/download/community) 7 o superior

Git, Python y Node se pueden instalar con winget:

```powershell
winget install Git.Git Python.Python.3.12 OpenJS.NodeJS.LTS
```

Para MongoDB, bajá el instalador `.msi` de la página oficial y dejá marcada la opción **Install MongoDB as a Service**, que viene así por defecto. MongoDB Compass y mongosh no hacen falta.

Al terminar, cerrá y volvé a abrir PowerShell para que reconozca los programas nuevos.

## 1. Clonar e instalar

```powershell
git clone https://github.com/mmmmor/kmr.git
cd kmr

cd backend
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cd ..\frontend
npm install
```

Si PowerShell no deja ejecutar `Activate.ps1`, corré `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` y volvé a intentar.

## 2. MongoDB local como replica set

La API usa transacciones, que en MongoDB solo funcionan en un replica set. Para convertir la instalación local en un replica set de un nodo:

1. Abrí PowerShell **como administrador**.
2. Abrí el archivo de configuración. El comando lo encuentra sin importar qué versión instalaste:
   ```powershell
   notepad (Resolve-Path "C:\Program Files\MongoDB\Server\*\bin\mongod.cfg")
   ```
3. Agregá estas dos líneas al final y guardá:
   ```yaml
   replication:
     replSetName: rs0
   ```
4. Reiniciá el servicio:
   ```powershell
   Restart-Service MongoDB
   ```
5. Iniciá el replica set. Esto se hace una sola vez y se corre desde `backend\`, con el entorno virtual activado:
   ```powershell
   python -c "from pymongo import MongoClient; print(MongoClient(directConnection=True).admin.command('replSetInitiate'))"
   ```
   Tiene que responder `{'ok': 1.0}`.

> **Alternativa:** también se puede usar un cluster gratuito de [MongoDB Atlas](https://www.mongodb.com/cloud/atlas/register) (M0), que ya es un replica set. En ese caso, saltá este paso, agregá tu IP en *Network Access* y usá su cadena `mongodb+srv://…` en `MONGODB_URI`.

## 3. Configurar y levantar la API

Desde `backend\`, con el entorno virtual activado:

```powershell
Copy-Item .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Abrí `backend\.env` y completá:

```
MONGODB_URI=mongodb://localhost:27017/?directConnection=true
JWT_SECRET=<la clave que generó el comando anterior>
```

Las demás variables pueden quedar como están. `BREVO_API_KEY` y `CORREO_REMITENTE` son para enviar el correo de recuperación de contraseña. Si quedan vacías, el enlace se escribe en la consola de la API.

Levantá la API:

```powershell
uvicorn app.main:app --reload
```

Para verificar que funciona:

- **http://localhost:8000/api/salud** tiene que responder `{"api":"ok","base_de_datos":"ok"}`.
- **http://localhost:8000/docs** muestra la documentación de los endpoints.

La base y sus índices se crean solos la primera vez.

## 4. Crear el administrador

El administrador no se registra desde la web. En otra terminal, desde `backend\` y con el entorno virtual activado:

```powershell
python -m scripts.crear_admin --correo admin@ejemplo.com --nombre Ana --apellido López
```

El script pide la contraseña dos veces. Tiene que tener entre 8 y 64 caracteres, al menos una mayúscula y un número.

## 5. Levantar el frontend

En otra terminal, desde `frontend\`:

```powershell
Copy-Item .env.example .env
npm run dev
```

Abrí **http://localhost:5173**.

Para recorrer todos los roles:

1. Registrá un **propietario** y vinculá un vehículo, por ejemplo `AE123CD`.
2. Desde **Soy taller**, pedí el alta de un **taller**.
3. Con el **administrador**, aprobá esa solicitud.
4. Como propietario, generá un código de autorización.
5. Como taller, usá el dominio y el código para registrar un servicio.
6. Sin sesión, buscá el dominio en el inicio para ver la consulta pública.

## Tests y lint

```powershell
# desde backend\ (con el entorno virtual activado)
pytest

# desde frontend\
npm run lint
npm run build
```

Los tests contra MongoDB se omiten salvo que definas `MONGODB_URI_TEST`. Usan una base aparte, `kmr_test`, y **la borran** al empezar:

```powershell
$env:MONGODB_URI_TEST = "mongodb://localhost:27017/?directConnection=true"; pytest
```

## Problemas frecuentes

| Síntoma | Solución |
|---|---|
| La API no arranca y menciona `jwt_secret` | Falta `JWT_SECRET` en `backend\.env`, o tiene menos de 32 caracteres. |
| `/api/salud` responde `sin_conexion` | Revisá que el servicio de MongoDB esté corriendo (`Get-Service MongoDB`) y que `MONGODB_URI` sea correcta. |
| `Transaction numbers are only allowed on a replica set member` | Falta el paso 2: MongoDB no está configurado como replica set. |
| `replSetInitiate` responde `already initialized` | El replica set ya estaba iniciado. No hace falta hacer nada. |
| Errores de CORS en el navegador | `FRONTEND_URL` (backend) y `VITE_API_URL` (frontend) tienen que coincidir con las direcciones reales. Reiniciá la API y el frontend después de cambiarlas. |
| `ModuleNotFoundError` | El entorno virtual no está activado, o no estás en `backend\`. |

Las reglas de negocio, el modelo de datos y los endpoints están documentados en [CLAUDE.md](CLAUDE.md).
