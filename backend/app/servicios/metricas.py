"""Métricas de mantenimiento de un vehículo (HU-013).

Se calculan sobre los servicios vigentes: si un registro fue corregido, cuenta su corrección y no
el original, y cada servicio se cuenta una sola vez.
"""

from collections import Counter

from app.esquemas.metricas import CantidadPorTipo, LecturaMetrica, MetricasSalida
from app.modelos.intervencion import Origen
from app.repositorios.intervenciones import RepositorioIntervenciones
from app.servicios import kilometraje

DIAS_POR_MES = 30


def calcular(registros: list[dict]) -> MetricasSalida:
    por_id = {r["_id"]: r for r in registros}
    servicios = sorted(
        kilometraje.lecturas_validas(registros),
        key=lambda r: (r["fecha_intervencion"], r["fecha_registro"], r["_id"]),
    )

    def original(registro):
        while registro.get("corrige_a") in por_id:
            registro = por_id[registro["corrige_a"]]
        return registro

    frecuencia_km = frecuencia_dias = uso_km_mes = None
    if len(servicios) >= 2:
        primero, ultimo = servicios[0], servicios[-1]
        km = ultimo["kilometraje"] - primero["kilometraje"]
        dias = (ultimo["fecha_intervencion"] - primero["fecha_intervencion"]).days
        intervalos = len(servicios) - 1
        frecuencia_dias = round(dias / intervalos)
        # Si el último kilometraje es menor al primero (hay inconsistencias), un promedio negativo no
        # dice nada: los de kilómetros quedan sin calcular.
        if km >= 0:
            frecuencia_km = round(km / intervalos)
            uso_km_mes = round(km / dias * DIAS_POR_MES) if dias > 0 else None

    tipos = Counter(r["tipo"] for r in servicios)
    origenes = Counter(r["origen"] for r in servicios)
    return MetricasSalida(
        servicios=len(servicios),
        correcciones=sum(1 for r in registros if r.get("corrige_a") is not None),
        frecuencia_km=frecuencia_km,
        frecuencia_dias=frecuencia_dias,
        uso_km_mes=uso_km_mes,
        por_tipo=[CantidadPorTipo(tipo=t, cantidad=c) for t, c in sorted(tipos.items(), key=lambda x: (-x[1], x[0]))],
        por_taller=origenes[Origen.TALLER],
        autorreportados=origenes[Origen.PROPIETARIO],
        lecturas=[
            LecturaMetrica(
                fecha=r["fecha_intervencion"],
                kilometraje=r["kilometraje"],
                valor_corregido=r["kilometraje"] != original(r)["kilometraje"],
            )
            for r in servicios
        ],
    )


async def obtener(vehiculo: dict, intervenciones: RepositorioIntervenciones) -> MetricasSalida:
    return calcular(await intervenciones.listar_por_vehiculo(vehiculo["_id"]))
