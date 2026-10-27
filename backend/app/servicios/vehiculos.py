from datetime import UTC, datetime

from bson import ObjectId

from app.esquemas.vehiculos import VehiculoEntrada, VehiculoSalida
from app.repositorios.vehiculos import DominioYaVinculado, RepositorioVehiculos


class VehiculoDeOtroPropietario(Exception):
    pass


class VehiculoYaVinculado(Exception):
    """El dominio ya está vinculado a la misma cuenta que lo intenta vincular."""


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


async def listar(propietario_id: str, vehiculos: RepositorioVehiculos) -> list[VehiculoSalida]:
    return [a_salida(v) for v in await vehiculos.listar_por_propietario(ObjectId(propietario_id))]


def a_salida(vehiculo: dict) -> VehiculoSalida:
    return VehiculoSalida(
        id=str(vehiculo["_id"]),
        dominio=vehiculo["dominio"],
        marca=vehiculo["marca"],
        modelo=vehiculo["modelo"],
        anio=vehiculo["anio"],
        fecha_vinculacion=vehiculo["fecha_vinculacion"],
    )
