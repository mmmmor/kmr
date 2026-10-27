"""Cadena de hash de las intervenciones de cada vehículo.

hash = SHA-256(json_canonico(registro) + hash_anterior), donde hash_anterior es el hash del
registro anterior del mismo vehículo (por fecha_registro), o vacío si es el primero.
"""

import hashlib
import json
from datetime import UTC, datetime

from bson import ObjectId

EXCLUIDOS = {"_id", "hash"}


def json_canonico(intervencion: dict) -> str:
    """Claves ordenadas, sin espacios, fechas en ISO 8601 UTC y ObjectId como texto. Excluye _id y hash."""
    campos = {clave: valor for clave, valor in intervencion.items() if clave not in EXCLUIDOS}
    return json.dumps(_normalizar(campos), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def calcular_hash(intervencion: dict, hash_anterior: str | None) -> str:
    contenido = json_canonico(intervencion) + (hash_anterior or "")
    return hashlib.sha256(contenido.encode("utf-8")).hexdigest()


def verificar_cadena(intervenciones: list[dict]) -> bool:
    """Recalcula la cadena de un vehículo siguiendo los enlaces hash_anterior → hash.

    Devuelve False si algún registro fue modificado, si falta uno intermedio o si dos
    registros dicen tener el mismo anterior.
    """
    por_anterior = {intervencion.get("hash_anterior"): intervencion for intervencion in intervenciones}
    if len(por_anterior) != len(intervenciones):
        return False
    hash_previo = None
    for _ in intervenciones:
        actual = por_anterior.get(hash_previo)
        if actual is None or actual.get("hash") != calcular_hash(actual, hash_previo):
            return False
        hash_previo = actual["hash"]
    return True


def _normalizar(valor):
    if isinstance(valor, dict):
        return {clave: _normalizar(v) for clave, v in valor.items()}
    if isinstance(valor, list):
        return [_normalizar(v) for v in valor]
    if isinstance(valor, ObjectId):
        return str(valor)
    if isinstance(valor, datetime):
        if valor.tzinfo is None:  # PyMongo sin tz_aware devuelve UTC sin zona.
            valor = valor.replace(tzinfo=UTC)
        return valor.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    return valor
