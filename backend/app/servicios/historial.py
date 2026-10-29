"""Historial de intervenciones (HU-012): línea de tiempo, correcciones e integridad.

También arma "Registros realizados" del taller, que muestra los mismos vínculos de corrección.
"""

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


def salidas(
    registros: list[dict], dominio: dict, razon_social: dict, referencias: dict
) -> list[IntervencionHistorialSalida]:
    """Los registros en el orden del historial, con sus vínculos de corrección.

    `dominio` y `razon_social` van por vehiculo_id y taller_id; `referencias`, por _id del registro
    (la lectura contra la que se validó su kilometraje).
    """
    por_id = {r["_id"]: r for r in registros}
    corregido_por = {}
    for registro in sorted(registros, key=lambda r: (r["fecha_registro"], r["_id"])):  # si hubo más de una, la última
        if registro.get("corrige_a") in por_id:
            corregido_por[registro["corrige_a"]] = registro

    def vinculado(registro):
        if registro is None:
            return None
        return RegistroVinculado(id=str(registro["_id"]), fecha=fecha_en_historial(registro))

    resultado = []
    for registro in ordenar(registros):
        base = servicio_intervenciones.a_salida(
            registro, dominio[registro["vehiculo_id"]], referencias.get(registro["_id"])
        )
        corregido = por_id.get(registro.get("corrige_a"))
        resultado.append(IntervencionHistorialSalida(
            **base.model_dump(),
            fecha=fecha_en_historial(registro),
            taller=razon_social.get(registro.get("taller_id")),
            corrige_a=vinculado(corregido),
            corregido_por=vinculado(corregido_por.get(registro["_id"])),
            motivo_correccion=registro.get("motivo_correccion"),
            campos_corregidos=campos_corregidos(registro, corregido),
        ))
    return resultado


async def obtener(
    vehiculo: dict, intervenciones: RepositorioIntervenciones, talleres: RepositorioTalleres
) -> HistorialSalida:
    """Historial completo de un vehículo para su propietario (HU-012)."""
    registros = await intervenciones.listar_por_vehiculo(vehiculo["_id"])  # en el orden de la cadena
    return HistorialSalida(
        vehiculo=servicio_vehiculos.a_salida(vehiculo, kilometraje.ultima_lectura(registros)),
        integridad_verificada=verificar_cadena(registros),
        intervenciones=salidas(
            registros,
            {vehiculo["_id"]: vehiculo["dominio"]},
            await _razones_sociales(registros, talleres),
            kilometraje.referencias(registros),
        ),
    )


async def listar_del_taller(
    taller: dict, intervenciones: RepositorioIntervenciones
) -> list[IntervencionHistorialSalida]:
    """Registros realizados por el taller. Solo él corrige sus registros: las correcciones también están acá."""
    registros = await intervenciones.listar_por_taller(taller["_id"])
    return salidas(
        registros,
        {r["vehiculo_id"]: r["dominio"] for r in registros},
        {taller["_id"]: taller["razon_social"]},
        await servicio_intervenciones.referencias_de_alertas(registros, intervenciones),
    )


async def _razones_sociales(registros: list[dict], talleres: RepositorioTalleres) -> dict:
    """Razón social de cada taller que cargó registros del vehículo (son pocos)."""
    razones = {}
    for taller_id in {r["taller_id"] for r in registros if r.get("taller_id") is not None}:
        taller = await talleres.buscar(taller_id)
        if taller is not None:
            razones[taller_id] = taller["razon_social"]
    return razones
