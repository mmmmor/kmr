"""Repositorios en memoria que imitan a los de MongoDB, para tests sin base."""

from datetime import UTC, datetime

from app.core.seguridad import hashear_contrasena
from app.repositorios.usuarios import CorreoYaRegistrado


class RepositorioUsuariosFalso:
    def __init__(self):
        self.usuarios: list[dict] = []

    async def insertar(self, usuario: dict) -> str:
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

    async def buscar_por_usuario(self, usuario_id) -> dict | None:
        return next((t for t in self.talleres if t["usuario_id"] == usuario_id), None)
