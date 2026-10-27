# Notas de sesión

Registro de lo hecho en cada sesión de trabajo, para retomar sin perder contexto. La fuente de verdad del producto sigue siendo el TFG y el `CLAUDE.md`; acá van el estado, las decisiones y su porqué.

---

## Sesión del 26 y 27 de octubre de 2026

**Resultado:** Sprint 1 completo (HU-001 a HU-004) en `main`, con CI y rama protegida.

### Estado al cierre

| Qué | Estado |
|---|---|
| Repo | https://github.com/mmmmor/kmr — **público**, rama `main` protegida |
| Sprint 1 | HU-001, HU-002, HU-003 y HU-004 mergeadas (PRs #4 a #8) |
| Tests | 80 tests en local + 6 de integración con MongoDB que corren en CI (86 en total) |
| Base de desarrollo | Cluster gratuito (M0) de MongoDB Atlas, MongoDB 8.0.34, base `kmr` |
| Próximo paso | Sprint 2, empezando por **HU-005 (vinculación de vehículos por dominio)** |

### Entorno y herramientas

- **Python 3.12.10** instalado con `py install 3.12` (la máquina tenía solo 3.15). Venv en `backend/.venv`.
- **Node v24.22.1 (LTS)** ya estaba en `C:\Program Files\nodejs`, pero fuera del PATH de algunas terminales.
- **GitHub CLI** instalado con winget (`C:\Program Files\GitHub CLI\gh.exe`), sesión de `mmmmor`.
- **Chrome** instalado para que Playwright pueda abrir la app y probar las pantallas.
- La rama principal se renombró de `master` a `main` antes de crear el repo.

### Repositorio, CI y protección

- Repo creado con `gh repo create` como privado y después pasado a **público**: la protección de ramas no está disponible en repos privados del plan gratuito. Antes de publicarlo se revisó el historial completo: no hay `.env`, URIs con contraseña ni tokens.
- **Protección de `main`:** exige que pasen `Backend (pytest)` y `Frontend (lint y build)`, con la rama actualizada; sin force push ni borrado; `enforce_admins` activado (aplica también al dueño).
- **CI (`.github/workflows/ci.yml`)** en cada PR y push a `main`:
  - Backend: pytest con un service `mongo:8.0` configurado como **replica set de un nodo** (`command: --replSet rs0`), porque la cadena de hash va a usar transacciones. El health check ejecuta `rs.initiate()` y da "healthy" recién cuando el nodo es primario. Sin credenciales.
  - Frontend: `npm ci`, `npm run lint` y `npm run build` con Node 24.
- Los tests de integración (`tests/test_mongodb.py`) solo corren si existe `MONGODB_URI_TEST`; en local se omiten y nunca escriben en Atlas.

### MongoDB Atlas

- Usuario de la app: `kmr_app` con `readWrite` **solo sobre la base `kmr`** (no `readWriteAnyDatabase` ni `atlasAdmin`).
- La URI vive en `backend/.env` (no se versiona). La contraseña se rotó porque había quedado escrita en el chat.
- `JWT_SECRET` local generado al azar en `backend/.env`.
- **Pendiente de revisar:** la lista de IPs del proyecto de Atlas tiene `0.0.0.0/0` ("Allow all (Railway)"), que parece de otro proyecto. Conviene borrarla o separar KmR en su propio proyecto de Atlas.

### Decisiones técnicas y su porqué

| Decisión | Por qué |
|---|---|
| **PyMongo async** (`AsyncMongoClient`) en vez de Motor | MongoDB deprecó Motor en 2025; PyMongo async es el reemplazo oficial e incluye GridFS async. El `CLAUDE.md` admitía cualquiera de los dos. |
| `httpx2` en vez de `httpx` para los tests | Starlette marca `httpx` como obsoleto para el TestClient. `httpx2` es el sucesor oficial (repo `pydantic/httpx2`, mismo autor). |
| ESLint (no Oxlint) en el frontend | create-vite 9 trae Oxlint por defecto; se eligió ESLint por ser el estándar y lo planificado. |
| React Router 8 (`react-router`) | Versión actual; conserva `BrowserRouter`, `Routes` y `Route`. |
| Timeout de selección de MongoDB de 5 s | Con 2 s la primera conexión a Atlas (DNS + TLS) podía dar falsos "sin conexión". |
| `JWT_SECRET` obligatoria (mínimo 32 caracteres) | Sin clave no se pueden firmar sesiones; la API no arranca sin ella. Hay que definirla en Render al desplegar. |
| Contraseñas: además de 8–64 caracteres, tope de **72 bytes** | bcrypt procesa como máximo 72 bytes; 64 caracteres con tildes o ñ pueden superarlos. |
| Login: hash de relleno con correo inexistente | Iguala el tiempo de respuesta para no revelar qué correos tienen cuenta. |
| Bloqueo: `$inc` atómico del contador | Evita carreras con intentos simultáneos. |
| Alta de taller en una **transacción** (`with_transaction`) | Si el correo o el CUIT ya existen, no queda un usuario sin solicitud. Verificado contra Atlas. |
| **CUIT:** 11 dígitos + dígito verificador (módulo 11) | Detecta errores de tipeo antes de que lleguen al administrador. Decidido mantenerlo. |
| CUIT con **máscara** en el formulario | Pedido del usuario: se tipean solo números, los guiones aparecen solos (`30-71589234-7`) y se guarda sin guiones. |
| Duplicados responden `409 { campos }` | El frontend marca el campo exacto (correo o CUIT). |
| Aprobar/rechazar con **update condicional** (`estado: pendiente`) | Si dos administradores resuelven a la vez, la segunda acción da `409`. |
| Rechazo: **solo motivo y fecha**, `aprobado_por` en `null` | Pedido del usuario: no registrar quién rechazó. Al aprobar sí se guarda el administrador. |
| Sesión del frontend en `sessionStorage` | Lo pide el `CLAUDE.md`; se descarta si el JWT venció y se borra al cerrar sesión. Con un `401` se vuelve al login. |
| Tipografías Space Grotesk, IBM Plex Sans e IBM Plex Mono | Coinciden con los mockups. |

### Lo implementado por historia de usuario

- **Base (PR #1):** FastAPI + config + conexión a MongoDB + `GET /api/salud`; React + Vite + React Router; `.env.example` y `.gitignore`.
- **HU-001 (PR #4):** `core/seguridad.py` (política de contraseñas, bcrypt, JWT HS256, `requiere_rol`), `POST /api/auth/registro`, índice único en `usuarios.correo`, errores `{ "campos": … }`, pantalla `/registro`.
- **HU-002 (PR #5):** `POST /api/auth/login`, mensaje genérico, bloqueo de 15 minutos tras 5 fallos, talleres pendientes o rechazados sin token, sesión en el frontend, rutas protegidas por rol y vistas provisorias por rol.
- **HU-003 (PR #6):** `POST /api/talleres/solicitud`, opción "Soy taller" del registro, índice único en `talleres.cuit`, máscara del CUIT.
- **HU-004 (PRs #7 y #8):** `GET /api/admin/solicitudes`, aprobar y rechazar, `scripts/crear_admin.py`, panel `/admin` con pestañas, verificación en ARCA y `LayoutPanel` reutilizable.

### Archivos principales

- **Backend:** `app/main.py`, `app/core/{config,db,seguridad,errores}.py`, `app/modelos/{usuario,taller}.py`, `app/esquemas/{auth,talleres,admin}.py`, `app/repositorios/{usuarios,talleres}.py`, `app/servicios/{auth,talleres,admin}.py`, `app/routers/{salud,auth,talleres,admin,dependencias}.py`, `scripts/crear_admin.py`.
- **Tests:** `tests/conftest.py`, `tests/falsos.py` (repositorios y transacción en memoria), `test_salud`, `test_seguridad`, `test_registro`, `test_login`, `test_solicitud_taller`, `test_admin_solicitudes`, `test_mongodb` (integración).
- **Frontend:** `src/api/{cliente,auth,talleres,admin}.js`, `src/auth/{sesion.js,contexto.js,SesionProvider.jsx,RutaProtegida.jsx}`, `src/components/{Logo,Campo,LayoutAcceso,LayoutPanel,PanelProvisorio}.jsx`, `src/pages/publico/{Inicio,Registro,Login,RecuperarContrasena}.jsx`, `src/pages/admin/{Solicitudes,DetalleSolicitud}.jsx`, `src/utils/{cuit,fechas}.js`.
- **Infra:** `.github/workflows/ci.yml`, `.gitignore`, `backend/.env.example`, `frontend/.env.example`.

### Problemas encontrados y cómo se resolvieron

| Problema | Solución |
|---|---|
| `node`/`npm` "no instalado" | Estaba instalado pero fuera del PATH de la terminal; se usa la ruta completa o se reinicia VS Code. |
| Sin Docker ni `mongod` local | Se usa Atlas para desarrollo y un service de MongoDB en CI. |
| Los services de GitHub Actions no aceptaban argumentos | La documentación actual sí admite `command`; se usó `--replSet rs0` y el health check inicia el replica set. |
| Protección de rama rechazada (403) | No existe en repos privados del plan gratuito; se publicó el repo. |
| El login no mostraba "Usuario o contraseña incorrectos" | `ErrorApi` trae `campos = {}` y la condición lo tomaba como error de campo. Se compara si hay campos. |
| "Soy propietario" partido en dos líneas en el celular | Íconos ocultos en pantallas chicas, como en el mockup móvil. |
| Barras de scroll de más en pestañas y navegación; iniciales del avatar descentradas | Línea de pestañas como sombra, `scrollbar-width: none` y selector CSS más específico. |
| `curl` de Git Bash rompe las tildes en JSON | Las cargas de prueba se hacen con Python (`urllib`). |
| Playwright no encontraba Chrome | `npx playwright install chrome`. Las capturas van a `.playwright-mcp/` (ignorada en git). |

### Pendiente

1. **Sprint 2:** HU-005 (vinculación por dominio: normalización `AAA111` / `AA111AA`, componente `Patente` con forma de placa, error si el vehículo pertenece a otro propietario, primera pantalla del propietario con `LayoutPanel`), luego HU-006, HU-007 y HU-008.
2. Sprint 3: HU-009 a HU-015 (kilometraje, consulta pública, correcciones, historial, métricas, alertas, recuperación de contraseña).
3. Crear tu administrador real con `scripts/crear_admin.py`.
4. Revisar la entrada `0.0.0.0/0` de la lista de IPs de Atlas.
5. Más adelante: `MONGODB_URI_INTERVENCIONES` (usuario solo `find`/`insert`), `backup.yml`, `vercel.json` y despliegue en Render/Vercel (definir `JWT_SECRET` y `FRONTEND_URL`).
6. Reemplazar las vistas provisorias de `/propietario`, `/taller`, `/recuperar` y la página de inicio a medida que lleguen sus HU.

### Cómo retomar

```powershell
# API (desde backend/)
.venv\Scripts\python.exe -m uvicorn app.main:app --reload    # http://localhost:8000/docs
.venv\Scripts\python.exe -m pytest

# Frontend (desde frontend/)
npm run dev                                                  # http://localhost:5173
npm run lint; npm run build

# Administrador (desde backend/)
.venv\Scripts\python.exe -m scripts.crear_admin --correo … --nombre … --apellido …
```

Flujo acordado: una rama `feature/hu-XXX-…` por historia, PR contra `main`, prueba en el navegador (escritorio y 390 px) con datos `@kmr.test` que se borran al final, y merge solo cuando el usuario lo pide.

### Memoria entre sesiones

Se instaló **claude-mem** (v15.3.0) a nivel usuario, con proveedor Claude local y sin cuenta online. Guarda sus datos en `~/.claude-mem` y no crea archivos en el repo. Como no captura lo anterior a su instalación, esta nota cubre todo lo hecho hasta ahora.
