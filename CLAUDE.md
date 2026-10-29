# KmR — Sistema de trazabilidad y verificación del historial de mantenimiento vehicular

Aplicación web donde talleres verificados y propietarios registran las intervenciones de mantenimiento de un vehículo en un historial **inmutable**, y donde cualquier persona puede consultar ese historial por dominio (patente) **sin ver datos personales del titular**.

Este proyecto es el Trabajo Final de Grado de Ingeniería en Software (Universidad Siglo 21). El documento del TFG es la fuente de verdad: si algo de este archivo choca con una regla de negocio de abajo, preguntá antes de cambiarla.

---

## Reglas para trabajar en este repo

- Respondé y escribí la interfaz en **español rioplatense** (voseo: "Ingresá", "Generá", "Conocé"). Código, nombres de variables, colecciones y endpoints también en español, en `snake_case` en Python y `camelCase` en JavaScript, siguiendo los nombres del modelo de datos de este archivo.
- Antes de implementar una historia de usuario, leé sus criterios de aceptación (sección "Historias de usuario") y escribí tests que los cubran.
- Nunca agregues operaciones de actualización o borrado sobre la colección `intervenciones`. Ver "Inmutabilidad".
- No guardes secretos en el código. Todo va por variables de entorno (ver `.env.example`).
- Cambios chicos y verificables. Corré los tests del backend (`pytest`) y el lint del frontend antes de dar algo por terminado.
- Los mockups de las pantallas están en `docs/mockups/`. Respetalos en estructura, textos y estilo.

---

## Stack

| Capa | Tecnología |
|---|---|
| Frontend | React + Vite (JavaScript), React Router, fetch/axios contra la API REST |
| Backend | Python 3.12 + FastAPI, Pydantic v2 para modelos y validación |
| Base de datos | MongoDB (driver async: Motor o PyMongo async). Comprobantes en GridFS |
| Contraseñas | bcrypt (con salt por usuario) |
| Sesión | JWT firmado (HS256), vence a las 2 horas |
| Correo | Brevo (API transaccional) para recuperación de contraseña |
| Control de versiones | Git + GitHub |
| Despliegue | Frontend en Vercel, backend en Render, base en MongoDB Atlas (M10 con Cloud Backup) |
| Respaldo externo | GitHub Actions + mongodump + GnuPG (AES-256) → Amazon S3 |

Arquitectura: el navegador carga el frontend (Vercel), que llama a la API REST (Render) por HTTPS. **El backend es el único componente que accede a MongoDB.** El backend también llama a Brevo para enviar correos.

---

## Estructura del repositorio

```
kmr/
├── CLAUDE.md
├── docs/
│   └── mockups/                # capturas de las pantallas del TFG
├── backend/
│   ├── app/
│   │   ├── main.py             # crea la app FastAPI, CORS, routers
│   │   ├── core/
│   │   │   ├── config.py       # settings desde variables de entorno
│   │   │   ├── seguridad.py    # bcrypt, JWT, dependencias de rol
│   │   │   └── db.py           # conexión Mongo, GridFS, índices
│   │   ├── modelos/            # modelos Pydantic de documentos y enums
│   │   ├── esquemas/           # esquemas de request/response (sin datos sensibles)
│   │   ├── repositorios/       # acceso a datos, uno por colección
│   │   ├── servicios/          # reglas de negocio (auth, codigos, intervenciones, kilometraje, hash, metricas, alertas, correo)
│   │   └── routers/            # endpoints agrupados por recurso
│   ├── scripts/
│   │   └── crear_admin.py      # alta interna del administrador
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── api/                # cliente HTTP y funciones por recurso
│   │   ├── auth/               # contexto de sesión, rutas protegidas por rol
│   │   ├── components/         # UI reutilizable (Patente, Badge, Timeline, etc.)
│   │   ├── pages/
│   │   │   ├── publico/        # inicio, consulta pública, login, registro, recuperación
│   │   │   ├── propietario/
│   │   │   ├── taller/
│   │   │   └── admin/
│   │   └── main.jsx
│   └── .env.example
└── .github/workflows/
    ├── ci.yml                  # tests backend + build frontend
    └── backup.yml              # respaldo diario a S3
```

---

## Roles

| Rol | Cómo se obtiene | Puede |
|---|---|---|
| Visitante | Sin cuenta | Consultar el historial público de un vehículo por dominio |
| Propietario | Registro público | Vincular vehículos, generar códigos de autorización, registrar intervenciones propias (autorreportadas), corregir sus autorreportadas, ver historial completo con métricas y alertas, consulta pública |
| Taller | Registro público + aprobación del administrador | Registrar intervenciones con un código vigente, corregir sus propios registros, ver sus registros realizados, consulta pública |
| Administrador | Alta interna (script), no hay registro público | Aprobar o rechazar solicitudes de talleres (el rechazo exige motivo) |

El rol viaja en el JWT. Cada endpoint protegido valida el rol con una dependencia de FastAPI (`requiere_rol("propietario")`, etc.). Un taller con solicitud pendiente o rechazada **no puede iniciar sesión**: el login informa el estado o el motivo de rechazo.

---

## Modelo de datos (MongoDB)

Los nombres siguen el diagrama de clases y el diagrama NoSQL del TFG. `→ coleccion` indica referencia por `ObjectId`. Todas las fechas se guardan en UTC y se muestran en hora de Argentina.

### `usuarios`
```
_id, nombre, apellido,
correo (único, en minúsculas),
contrasena_hash,
rol: "propietario" | "taller" | "administrador",
fecha_alta,
intentos_login_fallidos: int,     # operativo, para el bloqueo de 15 min
bloqueado_hasta: Date | null      # operativo
```

### `talleres`
```
_id, usuario_id → usuarios,
razon_social, cuit (único, 11 dígitos), domicilio, telefono,
estado_solicitud: "pendiente" | "aprobado" | "rechazado",
motivo_rechazo | null,
fecha_solicitud,
aprobado_por → usuarios | null,
fecha_resolucion | null
```

### `vehiculos`
```
_id, dominio (único, normalizado), marca, modelo, anio,
propietario_id → usuarios,
fecha_vinculacion
```

### `codigos_autorizacion`
```
_id, vehiculo_id → vehiculos,
codigo (6 dígitos),
fecha_generacion, fecha_vencimiento,
estado: "vigente" | "utilizado" | "invalidado",
intentos_fallidos: int,
taller_id → talleres | null,
fecha_uso | null
```
"Vencido" no se guarda como estado: se calcula (`estado == "vigente"` y `fecha_vencimiento < ahora`).

### `intervenciones` (solo lectura e inserción)
```
_id, vehiculo_id → vehiculos,
origen: "taller" | "propietario",
taller_id → talleres | null,
registrado_por → usuarios,
codigo_id → codigos_autorizacion | null,
fecha_intervencion, kilometraje: int,
tipo: str,                                   # ej. "Cambio de aceite y filtros", "Frenos"
descripcion: str | null,
items: [{ descripcion, cantidad }]            # al menos 1
proxima_revision: { kilometraje | null, fecha | null, detalle | null } | null,
comprobante_id: ObjectId (GridFS) | null,
alerta_kilometraje: "kilometraje_inferior" | "incremento_incompatible" | null,
corrige_a → intervenciones | null,
motivo_correccion | null,
fecha_registro,
hash_anterior | null,
hash
```

### `tokens_recuperacion`
```
_id, usuario_id → usuarios,
token_hash, fecha_vencimiento, utilizado: bool
```

### Índices
- `usuarios.correo` único; `talleres.cuit` único; `talleres.usuario_id` único; `vehiculos.dominio` único.
- `intervenciones`: `(vehiculo_id, fecha_registro)`, `taller_id`, `corrige_a`.
- `codigos_autorizacion`: `(vehiculo_id, estado)`.
- `tokens_recuperacion`: `token_hash`, y TTL sobre `fecha_vencimiento`.

---

## Reglas de negocio clave

### Inmutabilidad y correcciones
- Una intervención **nunca se modifica ni se elimina**. Los repositorios de `intervenciones` solo exponen `insertar` y consultas.
- La API se conecta a Atlas con un único usuario. Ese usuario solo tiene el rol personalizado `kmr_app`, definido en `backend/scripts/rol_app.py`:
  - sobre `intervenciones` permite solo `find` e `insert` (además de crear la colección y sus índices), así que la base rechaza cualquier modificación o borrado;
  - sobre el resto de las colecciones da las acciones que usa la API.
- Es un solo usuario y no dos, porque el registro del taller consume el código y guarda la intervención en la misma transacción, y una transacción no puede repartirse entre dos conexiones.
- Los tests de integración del CI corren la API con un usuario que tiene solo ese rol, y verifican que MongoDB rechaza modificar o borrar intervenciones.
- Si la API empieza a usar una colección o una operación nueva, hay que agregarla en `rol_app.py` y en el rol de Atlas.
- Una corrección es una **nueva intervención** con `corrige_a` apuntando a la original y `motivo_correccion` obligatorio. Conserva el registro previo y su autor.
- Un taller solo puede corregir intervenciones registradas por él mismo. Un propietario solo puede corregir sus intervenciones autorreportadas. Corregir no requiere un código nuevo.
- En el historial, la original se muestra marcada como "Corregido por el registro del dd/mm/aaaa" y la corrección como "Corrige el registro del dd/mm/aaaa". Ambas se ven siempre.

### Cadena de hash
- Cada intervención guarda `hash = SHA-256(json_canónico(campos del registro) + hash_anterior)`, donde `hash_anterior` es el `hash` de la intervención anterior **del mismo vehículo** (por `fecha_registro`), o `null` si es la primera.
- `json_canónico`: claves ordenadas, sin espacios, fechas en ISO 8601 UTC, ObjectId como string; excluye `_id` y `hash`.
- La inserción tiene que ser consistente ante dos cargas simultáneas para el mismo vehículo: leer el último hash y escribir dentro de una transacción, o reintentar si el `hash_anterior` cambió.
- `verificar_cadena(vehiculo)` recalcula toda la cadena. El historial muestra "Integridad verificada" si coincide y una alerta si no.

### Código temporal de autorización (HU-006)
- Lo genera el propietario para un vehículo suyo: 6 dígitos con `secrets`, vigencia de **24 horas**, un solo uso.
- Generar uno nuevo **invalida** el vigente anterior de ese vehículo.
- Un código vencido, utilizado o invalidado se rechaza con el mensaje "Código de autorización inválido o vencido".
- Cada ingreso erróneo de un código para un vehículo suma `intentos_fallidos` al código vigente. **Con 5 intentos fallidos, el sexto intento fallido invalida el código** y el propietario tiene que generar otro.
- Al registrarse la intervención, el código pasa a `utilizado` con `taller_id` y `fecha_uso`.
- La pantalla del propietario muestra el código vigente, cuándo vence, los intentos fallidos (x de 5) y la lista de códigos anteriores con su estado (Utilizado, Vencido, Invalidado).

### Validación del kilometraje (HU-009)
Al registrar una intervención o una corrección, se compara con la última lectura válida del vehículo (si un registro fue corregido, cuenta el valor de la corrección):
- Si el kilometraje es **menor** al último registrado → se guarda igual con `alerta_kilometraje = "kilometraje_inferior"`.
- Si el incremento es **incompatible con el tiempo transcurrido** → se guarda con `alerta_kilometraje = "incremento_incompatible"`. Criterio: promedio diario mayor a `KM_MAX_POR_DIA` (constante configurable, por defecto 500 km/día).
- Si es coherente → sin alerta.
- La primera intervención del vehículo no se valida.
- **Nunca se rechaza el registro por una alerta**: se guarda y queda visible.

### Alertas de servicio (HU-014)
Solo para intervenciones con `proxima_revision` definida:
- **Próximo:** faltan menos de 30 días para la fecha, o menos de 1.000 km respecto del último kilometraje registrado.
- **Vencido:** la fecha ya pasó o el kilometraje ya fue superado.
- Sin próxima revisión, no hay alerta.

### Métricas (HU-013)
- Con al menos 2 intervenciones: frecuencia promedio de mantenimiento en kilómetros y en días, y cantidad de intervenciones por tipo.
- Con 1 sola intervención: indicar que la frecuencia no puede calcularse.

### Dominio (patente)
- Formatos válidos: `AAA111` (viejo) y `AA111AA` (Mercosur).
- Normalizar antes de guardar o buscar: mayúsculas, sin espacios ni guiones. Regex: `^([A-Z]{3}\d{3}|[A-Z]{2}\d{3}[A-Z]{2})$`.
- Mostrar con formato de placa: `AE 123 CD`, `NTR 215`.

### Consulta pública (HU-010)
- No requiere cuenta. Devuelve, por intervención: fecha, kilometraje, tipo, ítems, origen (taller verificado con su razón social, o "Autorreportado por el propietario"), correcciones vinculadas, alertas y si tiene comprobante adjunto.
- **Nunca** incluye nombre, apellido, correo ni ningún dato del propietario, ni el `registrado_por`. Usá un esquema de respuesta propio para lo público; no reutilices el de los endpoints privados.
- El archivo del comprobante no es público (puede tener datos personales). Solo lo descargan el propietario del vehículo y el taller que lo cargó.
- Sin intervenciones: "No se registran intervenciones para el dominio consultado."

---

## Seguridad

Basada en las guías de OWASP (Authentication y Password Storage Cheat Sheets) y en la Ley 25.326 de Protección de los Datos Personales.

- **Identificación:** el correo es el nombre de usuario y es único.
- **Contraseña:** entre 8 y 64 caracteres, al menos una mayúscula y un número. El máximo existe porque bcrypt procesa como máximo 72 bytes. Si no cumple, se informa qué requisito falta.
- **Almacenamiento:** solo el hash bcrypt (con salt). Nunca texto plano ni logs de contraseñas.
- **Login:** ante credenciales incorrectas, mensaje genérico "Usuario o contraseña incorrectos" (sin decir cuál de los dos falló). Con **5 intentos fallidos consecutivos, la cuenta se bloquea 15 minutos**.
- **Sesión:** JWT firmado con `JWT_SECRET`, vence a las 2 horas, se envía en `Authorization: Bearer`. El frontend lo guarda en memoria o `sessionStorage` y lo borra al cerrar sesión.
- **Recuperación de contraseña:**
  - Se responde siempre el mismo mensaje, exista o no la cuenta.
  - Si existe, se envía por Brevo un enlace con un token aleatorio (`secrets.token_urlsafe`). Se guarda solo su hash, de un solo uso y con vencimiento a los 30 minutos.
  - Al cambiar la contraseña, el token queda invalidado.
- **Talleres:** no operan hasta que el administrador aprueba. El administrador verifica CUIT y razón social contra la constancia de inscripción de ARCA (verificación manual fuera del sistema).
- **Transporte:** todo por HTTPS/TLS. CORS restringido al dominio del frontend.
- **Secretos:** solo en variables de entorno de Render/Vercel/GitHub. `.env` en `.gitignore`.
- **Comprobantes:** PDF, JPG o PNG, hasta 5 MB. Validar el tipo real del archivo, no solo la extensión.

---

## Endpoints de la API (prefijo `/api`)

| Método | Ruta | Rol | Descripción |
|---|---|---|---|
| POST | `/auth/registro` | público | Alta de propietario (HU-001) |
| POST | `/auth/login` | público | Devuelve JWT y rol (HU-002) |
| POST | `/auth/recuperar` | público | Envía enlace de recuperación (HU-015) |
| POST | `/auth/restablecer` | público | Cambia la contraseña con el token (HU-015) |
| POST | `/talleres/solicitud` | público | Crea usuario taller + solicitud pendiente (HU-003) |
| GET | `/admin/solicitudes?estado=pendiente` | administrador | Lista solicitudes (HU-004) |
| POST | `/admin/solicitudes/{id}/aprobar` | administrador | Aprueba (HU-004) |
| POST | `/admin/solicitudes/{id}/rechazar` | administrador | Rechaza con motivo obligatorio (HU-004) |
| POST | `/vehiculos` | propietario | Vincula un vehículo por dominio (HU-005) |
| GET | `/vehiculos` | propietario | Mis vehículos |
| GET | `/vehiculos/{id}/historial` | propietario | Historial completo, orden cronológico (HU-012) |
| GET | `/vehiculos/{id}/metricas` | propietario | Métricas (HU-013) |
| GET | `/vehiculos/{id}/alertas` | propietario | Alertas de servicio (HU-014) |
| POST | `/vehiculos/{id}/codigos` | propietario | Genera código e invalida el anterior (HU-006) |
| GET | `/vehiculos/{id}/codigos` | propietario | Código vigente y anteriores (HU-006) |
| POST | `/vehiculos/{id}/intervenciones` | propietario | Intervención autorreportada (HU-008) |
| POST | `/taller/autorizacion` | taller | Valida dominio + código y devuelve el resumen del vehículo y el último km (HU-007) |
| POST | `/taller/intervenciones` | taller | Registra la intervención con dominio + código (multipart si hay comprobante) (HU-007) |
| GET | `/taller/intervenciones` | taller | Registros realizados por el taller |
| POST | `/intervenciones/{id}/correcciones` | taller o propietario | Corrección vinculada con motivo (HU-011) |
| GET | `/intervenciones/{id}/comprobante` | propietario del vehículo o taller autor | Descarga desde GridFS |
| GET | `/publico/vehiculos/{dominio}` | público | Historial público sin datos personales (HU-010) |

Errores: `HTTPException` con mensajes en español listos para mostrar en la interfaz. Los errores de validación de Pydantic se traducen a un formato `{ "campos": { "campo": "mensaje" } }` para marcar los campos faltantes en los formularios.

---

## Historias de usuario y orden de implementación

Implementá por sprint, en este orden. Cada HU tiene criterios de aceptación en formato Dado / Cuando / Entonces en el TFG; los puntos de abajo son su resumen.

### Sprint 1: usuarios y talleres
- **HU-001 Registro de usuario:** correo repetido → error; contraseña inválida → informar la restricción; campos incompletos → indicar cuáles; todo válido → crea la cuenta y redirige al login.
- **HU-002 Inicio de sesión:** credenciales correctas → vista según el rol; incorrectas → mensaje genérico; campo vacío → no continúa; taller pendiente o rechazado → informa estado o motivo; 5 fallos → bloqueo de 15 minutos.
- **HU-003 Solicitud de alta de taller:** razón social, CUIT, domicilio y teléfono → queda pendiente con aviso de revisión; CUIT repetido → error; campos incompletos → indicar cuáles; cuenta pendiente → no puede usarse.
- **HU-004 Aprobación de talleres:** listado de pendientes con sus datos; aprobar → `aprobado` y habilita el login; rechazar → exige motivo; sin solicitudes → "No hay solicitudes pendientes".

### Sprint 2: vehículos, códigos e intervenciones
- **HU-005 Vinculación por dominio:** dominio válido + marca, modelo y año → se asocia; formato inválido → error; vinculado a otra cuenta → "ese vehículo se encuentra vinculado a otro propietario", sin más datos.
- **HU-006 Código temporal:** ver reglas arriba.
- **HU-007 Registro por el taller:** dominio + código válido → habilita el formulario; datos completos (fecha, km, tipo, ítems) → se incorpora con la identificación del taller y la fecha y hora de carga; código inválido → "Código de autorización inválido o vencido". Flujo en 3 pasos: Autorización → Datos del servicio → Confirmación.
- **HU-008 Registro por el propietario:** se incorpora con la leyenda "Autorreportado por el propietario"; campos incompletos → indicar cuáles.

### Sprint 3: validación, consultas y extras
- **HU-009 Validación de kilometraje:** ver reglas arriba.
- **HU-010 Consulta pública:** ver reglas arriba.
- **HU-011 Correcciones:** ver reglas arriba.
- **HU-012 Historial del propietario:** orden cronológico; selector si tiene más de un vehículo; sin intervenciones → "Aún no se registran intervenciones para este vehículo."
- **HU-013 Métricas:** ver reglas arriba.
- **HU-014 Alertas de servicio:** ver reglas arriba.
- **HU-015 Recuperación de contraseña:** ver Seguridad.

---

## Interfaz

Basarse en `docs/mockups/`. Pantallas:

- **Pública:**
  - Inicio con buscador de dominio ("Conocé el mantenimiento real de un auto antes de comprarlo"), con tres tarjetas: registros que no se modifican, kilometraje contrastado, carga autorizada por el dueño.
  - Resultado de la consulta pública.
  - Login, registro y recuperación de contraseña.
- **Propietario:**
  - Barra lateral con Mis vehículos, Código de autorización, Registrar intervención y Consulta pública.
  - Vinculación de vehículo, historial con métricas y alertas, y generación de código.
- **Taller:**
  - Registrar intervención (stepper de 3 pasos, ítems dinámicos, próxima revisión opcional, comprobante opcional).
  - Registros realizados y consulta pública.
- **Administrador:** panel de solicitudes de talleres.

Estilo:
- Fondo `#F5F7F2`, tarjetas blancas con borde suave y esquinas redondeadas, color primario verde `#1F6B45`, alertas de inconsistencia en ámbar.
- Patentes dibujadas como placa:
  - Mercosur (`AA 111 AA`): franja azul "REPÚBLICA ARGENTINA".
  - Modelo anterior (`AAA 111`): chapa clara con el escudo arriba a la izquierda, "ARGENTINA" en celeste, ranuras de tornillos arriba y abajo, y un panel negro con caracteres blancos en relieve.
- Kilometrajes y códigos en tipografía monoespaciada.
- El historial es una línea de tiempo (del más reciente al más antiguo) con badges: "Taller verificado · {razón social}", "Autorreportado", "Inconsistencia", "Corrección", "Corrige el registro del …".
- Responsive: tiene que usarse bien desde el celular, porque los talleres cargan desde ahí.

---

## Variables de entorno

Backend (`backend/.env.example`):
```
MONGODB_URI=
MONGODB_DB=kmr
JWT_SECRET=
JWT_EXPIRA_MINUTOS=120
FRONTEND_URL=http://localhost:5173
BREVO_API_KEY=
CORREO_REMITENTE=
KM_MAX_POR_DIA=500
```

Frontend (`frontend/.env.example`):
```
VITE_API_URL=http://localhost:8000/api
```

---

## Comandos

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload           # http://localhost:8000/docs
pytest
python -m scripts.crear_admin           # crea el administrador

# Frontend
cd frontend
npm install
npm run dev                             # http://localhost:5173
npm run build
```

Para desarrollo local se puede usar MongoDB en Docker (`docker run -d -p 27017:27017 mongo:7`) o un cluster gratuito de Atlas. Las transacciones necesitan un replica set (Atlas lo trae por defecto).

---

## Tests mínimos (backend)

Tienen que existir tests para:
- Registro: correo duplicado, contraseña inválida, alta correcta.
- Login: mensaje genérico, bloqueo tras 5 fallos, taller pendiente o rechazado.
- Código: 6 dígitos, vencimiento a las 24 h, un solo uso, invalidación al generar otro, invalidación al sexto intento fallido.
- Intervenciones: no existe ruta ni método para editar o borrar; la corrección crea un registro nuevo vinculado; un taller no puede corregir registros de otro.
- Kilometraje: inferior, incremento incompatible, coherente, primera intervención.
- Cadena de hash: se encadena por vehículo y detecta alteraciones.
- Consulta pública: la respuesta no contiene ningún campo personal del propietario.
- Recuperación: misma respuesta con correo registrado o no, token de un solo uso y vencimiento a los 30 minutos.

---

## Despliegue y respaldo

- **Frontend:** Vercel, con `VITE_API_URL` apuntando al backend de Render.
- **Backend:** Render (Web Service), comando `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
- **Base:** MongoDB Atlas M10 con Cloud Backup activado.
  - El usuario de `MONGODB_URI` tiene solo el rol personalizado `kmr_app`.
  - Las acciones por colección se listan con `python -m scripts.rol_app --base kmr`.
- **Respaldo (regla 3-2-1, RPO 24 h, RTO 4 h):**
  1. Cloud Backup de Atlas: copias diarias (7 días), semanales (4 semanas) y mensuales (12 meses).
  2. `.github/workflows/backup.yml`: todos los días a las 03:00 de Argentina (`cron: "0 6 * * *"` en UTC), `mongodump` con un usuario de solo lectura, compresión, cifrado con GnuPG (AES-256) y subida a un bucket privado de Amazon S3. Secretos en GitHub Actions.
  3. Copia manual mensual en un disco externo cifrado (fuera del sistema).
- **Código:** GitHub; cada versión publicada lleva un tag (`v1.0.0`, …).
