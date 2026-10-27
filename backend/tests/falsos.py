"""Repositorios en memoria que imitan a los de MongoDB, para tests sin base."""

import copy
from datetime import UTC, datetime

from bson import ObjectId

from app.core.seguridad import hashear_contrasena
from app.repositorios.intervenciones import CadenaModificada
from app.repositorios.talleres import CuitYaRegistrado
from app.repositorios.usuarios import CorreoYaRegistrado
from app.repositorios.vehiculos import DominioYaVinculado


class RepositorioUsuariosFalso:
    def __init__(self):
        self.usuarios: list[dict] = []

    async def insertar(self, usuario: dict, sesion=None) -> str:
        if any(u["correo"] == usuario["correo"] for u in self.usuarios):
            raise CorreoYaRegistrado
        usuario = {"_id": f"id{len(self.usuarios) + 1}", **usuario}
        self.usuarios.append(usuario)
        return usuario["_id"]

    async def buscar_por_correo(self, correo: str) -> dict | None:
        return next((dict(u) for u in self.usuarios if u["correo"] == correo), None)

    async def sumar_intento_fallido(self, usuario_id) -> int:
        usuario = self._por_id(usuario_id)
        usuario["intentos_login_fallidos"] += 1
        return usuario["intentos_login_fallidos"]

    async def bloquear(self, usuario_id, hasta: datetime) -> None:
        self._por_id(usuario_id).update(bloqueado_hasta=hasta, intentos_login_fallidos=0)

    async def reiniciar_intentos(self, usuario_id) -> None:
        self._por_id(usuario_id).update(bloqueado_hasta=None, intentos_login_fallidos=0)

    def agregar(self, correo: str, contrasena: str, rol: str = "propietario", nombre: str = "Diego") -> dict:
        """Atajo para preparar un usuario ya registrado."""
        usuario = {
            "_id": f"id{len(self.usuarios) + 1}",
            "nombre": nombre,
            "apellido": "Paz",
            "correo": correo,
            "contrasena_hash": hashear_contrasena(contrasena),
            "rol": rol,
            "fecha_alta": datetime.now(UTC),
            "intentos_login_fallidos": 0,
            "bloqueado_hasta": None,
        }
        self.usuarios.append(usuario)
        return usuario

    def _por_id(self, usuario_id) -> dict:
        return next(u for u in self.usuarios if u["_id"] == usuario_id)


class RepositorioTalleresFalso:
    def __init__(self):
        self.talleres: list[dict] = []
        self.usuarios: RepositorioUsuariosFalso | None = None  # para el $lookup del responsable

    async def insertar(self, taller: dict, sesion=None) -> ObjectId:
        if any(t["cuit"] == taller["cuit"] for t in self.talleres if "cuit" in t):
            raise CuitYaRegistrado
        taller = {"_id": ObjectId(), **taller}
        self.talleres.append(taller)
        return taller["_id"]

    async def buscar_por_usuario(self, usuario_id) -> dict | None:
        return next((t for t in self.talleres if t["usuario_id"] == usuario_id), None)

    async def buscar(self, taller_id) -> dict | None:
        return next((t for t in self.talleres if t["_id"] == taller_id), None)

    async def listar_con_responsable(self, estado) -> list[dict]:
        en_estado = [t for t in self.talleres if t["estado_solicitud"] == estado.value]
        en_estado.sort(key=lambda t: t["fecha_solicitud"], reverse=True)
        return [{**t, "responsable": self.usuarios._por_id(t["usuario_id"])} for t in en_estado]

    async def resolver_pendiente(self, taller_id, estado, fecha, aprobado_por=None, motivo_rechazo=None) -> bool:
        taller = await self.buscar(taller_id)
        if taller is None or taller["estado_solicitud"] != "pendiente":
            return False
        taller.update(
            estado_solicitud=estado.value,
            motivo_rechazo=motivo_rechazo,
            aprobado_por=aprobado_por,
            fecha_resolucion=fecha,
        )
        return True


class RepositorioVehiculosFalso:
    def __init__(self):
        self.vehiculos: list[dict] = []

    async def insertar(self, vehiculo: dict) -> ObjectId:
        if any(v["dominio"] == vehiculo["dominio"] for v in self.vehiculos):
            raise DominioYaVinculado
        vehiculo = {"_id": ObjectId(), **vehiculo}
        self.vehiculos.append(vehiculo)
        return vehiculo["_id"]

    async def buscar(self, vehiculo_id) -> dict | None:
        return next((v for v in self.vehiculos if v["_id"] == vehiculo_id), None)

    async def buscar_por_dominio(self, dominio: str) -> dict | None:
        return next((v for v in self.vehiculos if v["dominio"] == dominio), None)

    async def listar_por_propietario(self, propietario_id) -> list[dict]:
        propios = [v for v in self.vehiculos if v["propietario_id"] == propietario_id]
        return sorted(propios, key=lambda v: v["fecha_vinculacion"])


class RepositorioCodigosFalso:
    def __init__(self):
        self.codigos: list[dict] = []
        self.talleres: RepositorioTalleresFalso | None = None  # para la razón social del taller

    async def insertar(self, codigo: dict, sesion=None) -> ObjectId:
        codigo = {"_id": ObjectId(), **codigo}
        self.codigos.append(codigo)
        return codigo["_id"]

    async def invalidar_vigentes(self, vehiculo_id, ahora, sesion=None) -> None:
        for codigo in self.codigos:
            if self._en_uso(codigo, vehiculo_id, ahora):
                codigo["estado"] = "invalidado"

    async def buscar_vigente(self, vehiculo_id, ahora) -> dict | None:
        en_uso = [c for c in self.codigos if self._en_uso(c, vehiculo_id, ahora)]
        return max(en_uso, key=lambda c: c["fecha_generacion"], default=None)

    async def listar_por_vehiculo(self, vehiculo_id) -> list[dict]:
        propios = [c for c in self.codigos if c["vehiculo_id"] == vehiculo_id]
        propios.sort(key=lambda c: c["fecha_generacion"], reverse=True)
        return [{**c, "taller": self._razon_social(c["taller_id"])} for c in propios]

    async def registrar_intento_fallido(self, codigo_id, maximo: int) -> None:
        codigo = self._por_id(codigo_id)
        if codigo["estado"] == "vigente":
            codigo["intentos_fallidos"] += 1
            if codigo["intentos_fallidos"] > maximo:
                codigo["estado"] = "invalidado"

    async def marcar_utilizado(self, codigo_id, taller_id, ahora, sesion=None) -> bool:
        codigo = self._por_id(codigo_id)
        if codigo["estado"] != "vigente" or codigo["fecha_vencimiento"] <= ahora:
            return False
        codigo.update(estado="utilizado", taller_id=taller_id, fecha_uso=ahora)
        return True

    @staticmethod
    def _en_uso(codigo, vehiculo_id, ahora) -> bool:
        return (
            codigo["vehiculo_id"] == vehiculo_id
            and codigo["estado"] == "vigente"
            and codigo["fecha_vencimiento"] > ahora
        )

    def _por_id(self, codigo_id) -> dict:
        return next(c for c in self.codigos if c["_id"] == codigo_id)

    def _razon_social(self, taller_id) -> str | None:
        if taller_id is None or self.talleres is None:
            return None
        return next(t["razon_social"] for t in self.talleres.talleres if t["_id"] == taller_id)


class RepositorioIntervencionesFalso:
    """Solo inserción y consultas, como el real. Imita el índice único (vehiculo_id, hash_anterior)."""

    def __init__(self):
        self.intervenciones: list[dict] = []
        self.vehiculos: RepositorioVehiculosFalso | None = None  # para el dominio del listado del taller

    async def insertar(self, intervencion: dict, sesion=None) -> ObjectId:
        clave = (intervencion["vehiculo_id"], intervencion["hash_anterior"])
        if any((i["vehiculo_id"], i["hash_anterior"]) == clave for i in self.intervenciones):
            raise CadenaModificada
        guardada = {"_id": ObjectId(), **copy.deepcopy(intervencion)}
        self.intervenciones.append(guardada)
        return guardada["_id"]

    async def buscar(self, intervencion_id) -> dict | None:
        return next((i for i in self.intervenciones if i["_id"] == intervencion_id), None)

    async def ultima_registrada(self, vehiculo_id, sesion=None) -> dict | None:
        del_vehiculo = [i for i in self.intervenciones if i["vehiculo_id"] == vehiculo_id]
        return max(del_vehiculo, key=lambda i: (i["fecha_registro"], i["_id"]), default=None)

    async def ultima_lectura(self, vehiculo_id) -> dict | None:
        del_vehiculo = [i for i in self.intervenciones if i["vehiculo_id"] == vehiculo_id]
        return max(del_vehiculo, key=lambda i: (i["fecha_intervencion"], i["fecha_registro"]), default=None)

    async def listar_por_vehiculo(self, vehiculo_id) -> list[dict]:
        del_vehiculo = [i for i in self.intervenciones if i["vehiculo_id"] == vehiculo_id]
        return sorted(del_vehiculo, key=lambda i: (i["fecha_registro"], i["_id"]))

    async def listar_por_taller(self, taller_id) -> list[dict]:
        del_taller = [i for i in self.intervenciones if i["taller_id"] == taller_id]
        del_taller.sort(key=lambda i: (i["fecha_registro"], i["_id"]), reverse=True)
        return [{**i, "dominio": (await self.vehiculos.buscar(i["vehiculo_id"]))["dominio"]} for i in del_taller]


class AlmacenComprobantesFalso:
    def __init__(self):
        self.archivos: dict[ObjectId, tuple[bytes, str, str]] = {}

    async def guardar(self, nombre: str, contenido: bytes, tipo: str) -> ObjectId:
        comprobante_id = ObjectId()
        self.archivos[comprobante_id] = (contenido, nombre, tipo)
        return comprobante_id

    async def leer(self, comprobante_id) -> tuple[bytes, str, str]:
        return self.archivos[comprobante_id]

    async def eliminar(self, comprobante_id) -> None:
        del self.archivos[comprobante_id]


class TransaccionFalsa:
    """Imita a `en_transaccion`: si la función falla, deshace lo que escribió en los repositorios."""

    def __init__(self, *repositorios):
        self.repositorios = repositorios

    async def __call__(self, funcion):
        # Solo se copian los datos (listas de documentos), no las referencias entre repositorios.
        copias = [
            {k: copy.deepcopy(v) for k, v in vars(repo).items() if isinstance(v, list)}
            for repo in self.repositorios
        ]
        try:
            return await funcion(None)
        except Exception:
            for repo, copia in zip(self.repositorios, copias):
                vars(repo).update(copia)
            raise
