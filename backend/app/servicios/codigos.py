"""Código temporal de autorización (HU-006): 6 dígitos, 24 horas de vigencia y un solo uso."""

import secrets
from datetime import UTC, datetime, timedelta

from bson import ObjectId

from app.esquemas.codigos import CodigoSalida, CodigosVehiculoSalida
from app.modelos.codigo import EstadoCodigo
from app.repositorios.codigos import RepositorioCodigos

VIGENCIA = timedelta(hours=24)
# Se toleran 5 intentos fallidos: el sexto invalida el código.
MAX_INTENTOS_FALLIDOS = 5

MENSAJE_CODIGO_INVALIDO = "Código de autorización inválido o vencido."


class CodigoInvalido(Exception):
    """El código no existe, no coincide, venció, ya se usó o fue invalidado."""


def generar_digitos() -> str:
    """Seis dígitos al azar con un generador criptográfico (incluye los que empiezan con 0)."""
    return f"{secrets.randbelow(10**6):06d}"


async def generar(vehiculo: dict, codigos: RepositorioCodigos, en_transaccion, ahora=None) -> CodigoSalida:
    """Genera un código nuevo e invalida el que estaba en uso, en una sola transacción."""
    ahora = ahora or datetime.now(UTC)
    nuevo = {
        "vehiculo_id": vehiculo["_id"],
        "codigo": generar_digitos(),
        "fecha_generacion": ahora,
        "fecha_vencimiento": ahora + VIGENCIA,
        "estado": EstadoCodigo.VIGENTE.value,
        "intentos_fallidos": 0,
        "taller_id": None,
        "fecha_uso": None,
    }

    async def reemplazar(sesion):
        await codigos.invalidar_vigentes(vehiculo["_id"], ahora, sesion=sesion)
        return await codigos.insertar(dict(nuevo), sesion=sesion)

    codigo_id = await en_transaccion(reemplazar)
    return _a_salida({"_id": codigo_id, **nuevo}, ahora)


async def listar(vehiculo: dict, codigos: RepositorioCodigos, ahora=None) -> CodigosVehiculoSalida:
    """El código en uso (si hay) y los anteriores, del más reciente al más antiguo."""
    ahora = ahora or datetime.now(UTC)
    salidas = [_a_salida(codigo, ahora) for codigo in await codigos.listar_por_vehiculo(vehiculo["_id"])]
    vigente = next((c for c in salidas if c.estado == "vigente"), None)
    return CodigosVehiculoSalida(
        vigente=vigente,
        anteriores=[c for c in salidas if c is not vigente],
        max_intentos_fallidos=MAX_INTENTOS_FALLIDOS,
    )


async def validar(vehiculo_id: ObjectId, ingresado: str, codigos: RepositorioCodigos, ahora=None) -> dict:
    """Devuelve el código en uso si coincide con el ingresado. Si no, lanza CodigoInvalido.

    Un ingreso erróneo suma un intento fallido al código en uso; al sexto, el código queda invalidado.
    """
    ahora = ahora or datetime.now(UTC)
    vigente = await codigos.buscar_vigente(vehiculo_id, ahora)
    if vigente is None:
        raise CodigoInvalido
    if not secrets.compare_digest(vigente["codigo"].encode(), ingresado.encode()):
        await codigos.registrar_intento_fallido(vigente["_id"], MAX_INTENTOS_FALLIDOS)
        raise CodigoInvalido
    return vigente


async def consumir(codigo: dict, taller_id: ObjectId, codigos: RepositorioCodigos, ahora=None, sesion=None) -> None:
    """Marca el código como utilizado por el taller. Si otro pedido lo usó antes, lanza CodigoInvalido."""
    ahora = ahora or datetime.now(UTC)
    if not await codigos.marcar_utilizado(codigo["_id"], taller_id, ahora, sesion=sesion):
        raise CodigoInvalido


def _a_salida(codigo: dict, ahora: datetime) -> CodigoSalida:
    estado = codigo["estado"]
    if estado == EstadoCodigo.VIGENTE and codigo["fecha_vencimiento"] <= ahora:
        estado = "vencido"
    return CodigoSalida(
        id=str(codigo["_id"]),
        codigo=codigo["codigo"],
        estado=estado,
        fecha_generacion=codigo["fecha_generacion"],
        fecha_vencimiento=codigo["fecha_vencimiento"],
        intentos_fallidos=codigo["intentos_fallidos"],
        taller=codigo.get("taller"),
        fecha_uso=codigo.get("fecha_uso"),
    )
