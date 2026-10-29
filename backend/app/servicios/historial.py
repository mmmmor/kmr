"""Historial de intervenciones de un vehículo (HU-012): línea de tiempo, correcciones e integridad."""

from collections import defaultdict
from datetime import datetime

from app.esquemas.historial import HistorialSalida, IntervencionHistorialSalida, RegistroVinculado
from app.repositorios.intervenciones import RepositorioIntervenciones
from app.repositorios.talleres import RepositorioTalleres
from app.servicios import intervenciones as servicio_intervenciones
from app.servicios import kilometraje
from app.servicios import vehiculos as servicio_vehiculos
from app.servicios.hash import verificar_cadena

# Datos de un registro que una corrección puede cambiar.
CAMPOS_CORREGIBLES = ("fecha_intervencion", "kilometraje", "tipo", "descripcion", "items", "proxima_revision")


def fecha_en_historial(registro: dict) -> datetime:
    """La fecha del servicio; una corrección se muestra con el día en que se cargó."""
    return registro["fecha_registro"] if registro.get("corrige_a") is not None else registro["fecha_intervencion"]


def ordenar(registros: list[dict]) -> list[dict]:
    """Del más reciente al más antiguo. Cada corrección va justo arriba del registro que corrige.

    Un registro y sus correcciones forman un grupo que se ordena por la fecha de servicio vigente
    (la de su última corrección), así una corrección de fecha también lo reubica.
    """
    por_id = {r["_id"]: r for r in registros}

    def original(registro):
        while registro.get("corrige_a") in por_id:
            registro = por_id[registro["corrige_a"]]
        return registro

    grupos = defaultdict(list)
    for registro in registros:
        grupos[original(registro)["_id"]].append(registro)
    for grupo in grupos.values():
        grupo.sort(key=lambda r: (r["fecha_registro"], r["_id"]), reverse=True)  # el original queda al final

    def clave(grupo):
        vigente, inicial = grupo[0], grupo[-1]
        return vigente["fecha_intervencion"], inicial["fecha_registro"], inicial["_id"]

    return [registro for grupo in sorted(grupos.values(), key=clave, reverse=True) for registro in grupo]


def campos_corregidos(correccion: dict, corregido: dict | None) -> list[str]:
    if corregido is None:
        return []
    return [campo for campo in CAMPOS_CORREGIBLES if correccion.get(campo) != corregido.get(campo)]


async def obtener(
    vehiculo: dict, intervenciones: RepositorioIntervenciones, talleres: RepositorioTalleres
) -> HistorialSalida:
    registros = await intervenciones.listar_por_vehiculo(vehiculo["_id"])  # en el orden de la cadena
    por_id = {r["_id"]: r for r in registros}
    referencias = kilometraje.referencias(registros)
    razon_social = await _razones_sociales(registros, talleres)

    corregido_por = {}
    for registro in registros:  # en orden de carga: si hubo más de una, queda la última
        if registro.get("corrige_a") in por_id:
            corregido_por[registro["corrige_a"]] = registro

    def vinculado(registro):
        if registro is None:
            return None
        return RegistroVinculado(id=str(registro["_id"]), fecha=fecha_en_historial(registro))

    salidas = []
    for registro in ordenar(registros):
        base = servicio_intervenciones.a_salida(registro, vehiculo["dominio"], referencias.get(registro["_id"]))
        corregido = por_id.get(registro.get("corrige_a"))
        salidas.append(IntervencionHistorialSalida(
            **base.model_dump(),
            fecha=fecha_en_historial(registro),
            taller=razon_social.get(registro.get("taller_id")),
            corrige_a=vinculado(corregido),
            corregido_por=vinculado(corregido_por.get(registro["_id"])),
            motivo_correccion=registro.get("motivo_correccion"),
            campos_corregidos=campos_corregidos(registro, corregido),
        ))

    return HistorialSalida(
        vehiculo=servicio_vehiculos.a_salida(vehiculo, kilometraje.ultima_lectura(registros)),
        integridad_verificada=verificar_cadena(registros),
        intervenciones=salidas,
    )


async def _razones_sociales(registros: list[dict], talleres: RepositorioTalleres) -> dict:
    """Razón social de cada taller que cargó registros del vehículo (son pocos)."""
    razones = {}
    for taller_id in {r["taller_id"] for r in registros if r.get("taller_id") is not None}:
        taller = await talleres.buscar(taller_id)
        if taller is not None:
            razones[taller_id] = taller["razon_social"]
    return razones
