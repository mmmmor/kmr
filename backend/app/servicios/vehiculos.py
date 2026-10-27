from datetime import UTC, datetime

from bson import ObjectId
from bson.errors import InvalidId

from app.esquemas.vehiculos import UltimaLectura, VehiculoEntrada, VehiculoSalida
from app.repositorios.intervenciones import RepositorioIntervenciones
from app.repositorios.vehiculos import DominioYaVinculado, RepositorioVehiculos


class VehiculoDeOtroPropietario(Exception):
    pass


class VehiculoYaVinculado(Exception):
    """El dominio ya está vinculado a la misma cuenta que lo intenta vincular."""


class VehiculoNoEncontrado(Exception):
    pass


async def vincular(datos: VehiculoEntrada, propietario_id: str, vehiculos: RepositorioVehiculos) -> VehiculoSalida:
    """Asocia el vehículo a la cuenta del propietario (HU-005).

    Se inserta directamente y el índice único sobre `dominio` decide: así dos altas
    simultáneas del mismo dominio no pueden quedar vinculadas a cuentas distintas.
    """
    propietario = ObjectId(propietario_id)
    vehiculo = {
        "dominio": datos.dominio,
        "marca": datos.marca,
        "modelo": datos.modelo,
        "anio": datos.anio,
        "propietario_id": propietario,
        "fecha_vinculacion": datetime.now(UTC),
    }
    try:
        vehiculo_id = await vehiculos.insertar(vehiculo)
    except DominioYaVinculado:
        existente = await vehiculos.buscar_por_dominio(datos.dominio)
        if existente is not None and existente["propietario_id"] == propietario:
            raise VehiculoYaVinculado
        raise VehiculoDeOtroPropietario
    return a_salida({"_id": vehiculo_id, **vehiculo})


async def listar(
    propietario_id: str, vehiculos: RepositorioVehiculos, intervenciones: RepositorioIntervenciones
) -> list[VehiculoSalida]:
    """Vehículos del propietario con su último kilometraje registrado (una consulta por vehículo: son pocos)."""
    salidas = []
    for vehiculo in await vehiculos.listar_por_propietario(ObjectId(propietario_id)):
        ultima = await intervenciones.ultima_lectura(vehiculo["_id"])
        salidas.append(a_salida(vehiculo, ultima))
    return salidas


async def obtener_propio(vehiculo_id: str, propietario_id: str, vehiculos: RepositorioVehiculos) -> dict:
    """Devuelve el vehículo solo si pertenece al propietario.

    Si no existe o es de otra cuenta lanza VehiculoNoEncontrado en los dos casos, para no
    revelar qué vehículos tienen otros propietarios.
    """
    try:
        vehiculo = await vehiculos.buscar(ObjectId(vehiculo_id))
    except (InvalidId, TypeError):
        raise VehiculoNoEncontrado
    if vehiculo is None or vehiculo["propietario_id"] != ObjectId(propietario_id):
        raise VehiculoNoEncontrado
    return vehiculo


def a_salida(vehiculo: dict, ultima: dict | None = None) -> VehiculoSalida:
    """`ultima`: la intervención con la fecha de servicio más reciente, si hay."""
    return VehiculoSalida(
        id=str(vehiculo["_id"]),
        dominio=vehiculo["dominio"],
        marca=vehiculo["marca"],
        modelo=vehiculo["modelo"],
        anio=vehiculo["anio"],
        fecha_vinculacion=vehiculo["fecha_vinculacion"],
        ultima_lectura=None if ultima is None else UltimaLectura(
            kilometraje=ultima["kilometraje"], fecha=ultima["fecha_intervencion"]
        ),
    )
