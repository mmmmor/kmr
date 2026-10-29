# KmR

Sistema de trazabilidad y verificación del historial de mantenimiento vehicular. Talleres verificados y propietarios registran las intervenciones de un vehículo en un historial inmutable, y cualquier persona puede consultarlo por dominio sin ver datos personales del titular.

Trabajo Final de Grado de Ingeniería en Software (Universidad Siglo 21).

- **Frontend:** React + Vite.
- **Backend:** Python 3.12 + FastAPI.
- **Base de datos:** MongoDB.

Esta guía explica cómo dejarlo corriendo en una computadora nueva, desde cero.

---

## Requisitos

| Herramienta | Versión | Para qué |
|---|---|---|
| [Git](https://git-scm.com/downloads) | cualquiera reciente | clonar el repositorio |
| [Python](https://www.python.org/downloads/) | **3.12** | backend |
| [Node.js](https://nodejs.org/) | **20.19 o superior** (recomendado 24 LTS) | frontend |
| MongoDB | 7 u 8, **con replica set** | base de datos |

MongoDB tiene que funcionar como replica set porque la API usa transacciones. Hay dos formas de tenerlo:

- **MongoDB Atlas (recomendado):** un cluster gratuito M0 ya viene como replica set. No hace falta instalar nada.
- **Docker:** un contenedor local configurado como replica set de un nodo.

Verificá las versiones:

```bash
git --version
python --version     # en Windows: py -3.12 --version
node --version
```

> **Windows:** si no tenés Python 3.12, instalalo desde python.org o con `py install 3.12`. Los comandos de esta guía usan `py -3.12` para elegir esa versión aunque tengas otras instaladas.

---

## 1. Clonar el repositorio

```bash
git clone https://github.com/mmmmor/kmr.git
cd kmr
```

---

## 2. Preparar la base de datos

Elegí **una** de las dos opciones. Al final vas a tener la cadena de conexión que va en `MONGODB_URI`.

### Opción A: MongoDB Atlas (gratis)

1. Creá una cuenta en [mongodb.com/atlas](https://www.mongodb.com/cloud/atlas/register).
2. Creá un cluster **M0 (Free)**.
3. En **Database Access**, creá un usuario de base de datos con contraseña y el rol *Read and write to any database*.
4. En **Network Access**, agregá tu IP actual. Para desarrollo también podés usar `0.0.0.0/0`, que permite conexiones desde cualquier IP.
5. En el cluster, entrá a **Connect → Drivers** y copiá la cadena de conexión. Tiene esta forma:
   ```
   mongodb+srv://<usuario>:<contraseña>@<cluster>.mongodb.net/?retryWrites=true&w=majority
   ```
   Reemplazá `<usuario>` y `<contraseña>` por los del paso 3. Si la contraseña tiene caracteres especiales (`@`, `:`, `/`, `#`), codificalos en formato URL (por ejemplo, `@` se escribe `%40`).

No hace falta crear la base ni las colecciones: la API las crea, con sus índices, la primera vez que arranca.

### Opción B: MongoDB local con Docker

Necesitás [Docker](https://docs.docker.com/get-docker/) instalado y corriendo.

```bash
docker run -d --name kmr-mongo -p 27017:27017 mongo:7.0 --replSet rs0
docker exec kmr-mongo mongosh --quiet --eval "rs.initiate()"
```

El segundo comando inicia el replica set. Se corre una sola vez: los datos y la configuración quedan en el contenedor.

La cadena de conexión es:

```
mongodb://localhost:27017/?directConnection=true
```

Para las sesiones siguientes alcanza con `docker start kmr-mongo`.

---

## 3. Backend

Todos los comandos de esta sección se corren desde la carpeta `backend/`.

### Entorno virtual y dependencias

**macOS / Linux**

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Windows (PowerShell)**

```powershell
cd backend
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Si PowerShell no deja ejecutar `Activate.ps1`, habilitá los scripts solo para esa terminal y volvé a activar:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.venv\Scripts\Activate.ps1
```

Cuando el entorno está activo, el prompt empieza con `(.venv)`. Tenés que activarlo en cada terminal nueva antes de usar `uvicorn`, `pytest` o los scripts.

### Variables de entorno

Copiá el archivo de ejemplo:

```bash
cp .env.example .env              # Windows: Copy-Item .env.example .env
```

Abrí `backend/.env` y completá:

| Variable | Valor |
|---|---|
| `MONGODB_URI` | La cadena de conexión del paso 2. |
| `JWT_SECRET` | Una clave aleatoria de al menos 32 caracteres (comando abajo). Sin ella la API no arranca. |

Para generar la clave:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

El resto puede quedar como está para desarrollo local:

| Variable | Por defecto | Notas |
|---|---|---|
| `MONGODB_DB` | `kmr` | Nombre de la base. |
| `JWT_EXPIRA_MINUTOS` | `120` | Duración de la sesión. |
| `FRONTEND_URL` | `http://localhost:5173` | Única dirección que la API acepta por CORS. Si cambiás el puerto del frontend, cambiala también acá. |
| `BREVO_API_KEY`, `CORREO_REMITENTE` | vacías | Sin ellas, el enlace de recuperación de contraseña no se envía por correo: se escribe en la consola de la API (ver más abajo). |
| `KM_MAX_POR_DIA` | `500` | Tope de km por día que usa la validación de kilometraje. |
| `MONGODB_URI_INTERVENCIONES` | vacía | Reservada para producción. Todavía no se usa. |

`.env` está en `.gitignore`. No lo subas al repositorio.

### Levantar la API

```bash
uvicorn app.main:app --reload
```

Para verificar que funciona:

- **http://localhost:8000/api/salud** tiene que responder `{"api":"ok","base_de_datos":"ok"}`.
- **http://localhost:8000/docs** muestra la documentación interactiva de todos los endpoints.

Si `base_de_datos` dice `sin_conexion`, revisá [Problemas frecuentes](#problemas-frecuentes).

### Crear el administrador

El administrador no se registra desde la web: se crea con un script. En otra terminal, con el entorno activado y desde `backend/`:

```bash
python -m scripts.crear_admin --correo admin@ejemplo.com --nombre Ana --apellido López
```

El script te pide la contraseña dos veces, sin mostrarla. Tiene que tener entre 8 y 64 caracteres, al menos una mayúscula y un número.

---

## 4. Frontend

En otra terminal, desde la raíz del repositorio:

```bash
cd frontend
npm install
cp .env.example .env              # Windows: Copy-Item .env.example .env
npm run dev
```

Abrí **http://localhost:5173**.

`VITE_API_URL` (en `frontend/.env`) ya apunta a `http://localhost:8000/api`. Cambiala solo si la API corre en otra dirección.

---

## 5. Primer recorrido

Con la API y el frontend corriendo, este recorrido prueba todos los roles. Los correos pueden ser inventados: la verificación del correo no es parte del sistema.

1. **Propietario.**
   - Entrá a **Crear cuenta** y registrate.
   - Iniciá sesión, entrá a *Mis vehículos* y vinculá un vehículo con un dominio válido, por ejemplo `AE123CD` o `NTR215`.
2. **Taller.**
   - Cerrá sesión y entrá a **Soy taller** (`/registro?tipo=taller`).
   - Completá la solicitud con un CUIT de 11 dígitos.
   - Si intentás iniciar sesión, el sistema avisa que la solicitud está pendiente.
3. **Administrador.**
   - Iniciá sesión con la cuenta que creaste con el script.
   - Aprobá la solicitud del taller.
4. **Código de autorización.** Como propietario, entrá a *Código de autorización* y generá un código de 6 dígitos.
5. **Registro del taller.**
   - Como taller, entrá a *Registrar intervención* e ingresá el dominio y el código.
   - Cargá el servicio: fecha, kilometraje, tipo e ítems.
6. **Historial y consulta pública.**
   - Como propietario, abrí el vehículo para ver el historial, las métricas y las alertas.
   - Desde el inicio, sin sesión, buscá el dominio para ver la consulta pública.

### Recuperar la contraseña sin Brevo

Sin `BREVO_API_KEY`, la recuperación funciona igual, pero el correo no se envía:

1. Entrá a **¿Olvidaste tu contraseña?** en el login e ingresá un correo registrado.
2. En la terminal de la API aparece una línea con el enlace de recuperación. Abrilo en el navegador.

El enlace vence a los 30 minutos y sirve una sola vez.

---

## Tests y lint

**Backend**, desde `backend/` con el entorno activado:

```bash
pytest
```

Los tests de integración contra MongoDB (`tests/test_mongodb.py`) se omiten salvo que definas `MONGODB_URI_TEST`. Usan una base aparte, `kmr_test`, y **la borran** al empezar. No uses la cadena de una base con datos que te importen.

Por ejemplo, con el Mongo de Docker:

```bash
MONGODB_URI_TEST="mongodb://localhost:27017/?directConnection=true" pytest
# Windows: $env:MONGODB_URI_TEST="mongodb://localhost:27017/?directConnection=true"; pytest
```

**Frontend**, desde `frontend/`:

```bash
npm run lint
npm run build
```

GitHub Actions (`.github/workflows/ci.yml`) corre lo mismo en cada pull request, con los tests de MongoDB incluidos.

---

## Problemas frecuentes

| Síntoma | Causa y solución |
|---|---|
| La API no arranca y menciona `jwt_secret` | Falta `JWT_SECRET` en `backend/.env` o tiene menos de 32 caracteres. |
| `/api/salud` responde `sin_conexion` o la API tarda y falla al arrancar | Mongo no es alcanzable. Con Atlas, revisá que tu IP esté en *Network Access* y que el usuario y la contraseña de la cadena sean correctos. Con Docker, revisá que el contenedor esté corriendo (`docker ps`). |
| `Transaction numbers are only allowed on a replica set member or mongos` | Mongo no corre como replica set. Con Docker, creá el contenedor con `--replSet rs0` y corré `rs.initiate()` (paso 2, opción B). |
| El navegador muestra errores de CORS o el frontend no puede conectarse | `FRONTEND_URL` del backend no coincide con la dirección del frontend, o `VITE_API_URL` no apunta a la API. Después de cambiar un `.env`, reiniciá el proceso correspondiente. |
| `ModuleNotFoundError` al correr `uvicorn` o el script | El entorno virtual no está activado, o no estás en la carpeta `backend/`. |
| PowerShell no deja ejecutar `Activate.ps1` | Corré `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` en esa terminal. |
| `npm run dev` falla con un error de versión de Node | Vite necesita Node 20.19 o superior. Actualizá Node. |

---

## Estructura

```
kmr/
├── backend/            API FastAPI (app/), tests y scripts/crear_admin.py
├── frontend/           SPA React + Vite
├── docs/mockups/       pantallas de referencia del TFG
└── .github/workflows/  CI
```

Las reglas de negocio, el modelo de datos y los endpoints están documentados en [CLAUDE.md](CLAUDE.md).
