"""HU-013: métricas de mantenimiento. Usa repositorios y transacción en memoria."""

from datetime import datetime, timedelta

from bson import ObjectId

from app.core.fechas import hoy_en_argentina, inicio_del_dia
from app.modelos.usuario import Rol
from tests.test_historial import _cargar, _taller
from tests.test_intervencion_propietario import _token, repos  # noqa: F401 (fixture)

ACEITE = "Cambio de aceite y filtros"


def _metricas(cliente, repos, headers=None):
    return cliente.get(f"/api/vehiculos/{repos.vehiculo['_id']}/metricas", headers=headers or repos.headers)


def _historial_del_mockup(repos):
    """Los servicios del mockup: 12/09/2025, 20/03/2026, 18/06/2026 (corregido) y 14/08/2026."""
    taller = _taller(repos)
    _cargar(repos, 72300, 346, taller=taller)
    _cargar(repos, 84100, 157)
    con_error = _cargar(repos, 48100, 67, tipo="Frenos", taller=taller)
    _cargar(repos, 91800, 67, tipo="Frenos", taller=taller, corrige=con_error, motivo="Error de tipeo.")
    _cargar(repos, 98450, 10, taller=taller)


def test_frecuencia_promedio_en_km_y_dias_con_los_valores_corregidos(cliente, repos):
    _historial_del_mockup(repos)

    metricas = _metricas(cliente, repos).json()

    assert metricas["servicios"] == 4, "la corrección no es un servicio más"
    assert metricas["correcciones"] == 1
    assert metricas["frecuencia_km"] == 8717  # (98.450 - 72.300) / 3
    assert metricas["frecuencia_dias"] == 112  # 336 días / 3
    assert metricas["uso_km_mes"] == 2335  # 26.150 km en 336 días, por 30


def test_cantidad_por_tipo_y_por_origen(cliente, repos):
    _historial_del_mockup(repos)

    metricas = _metricas(cliente, repos).json()

    assert metricas["por_tipo"] == [{"tipo": ACEITE, "cantidad": 3}, {"tipo": "Frenos", "cantidad": 1}]
    assert (metricas["por_taller"], metricas["autorreportados"]) == (3, 1)


def test_las_lecturas_del_grafico_usan_el_valor_corregido(cliente, repos):
    _historial_del_mockup(repos)

    lecturas = _metricas(cliente, repos).json()["lecturas"]

    assert [(lectura["kilometraje"], lectura["valor_corregido"]) for lectura in lecturas] == [
        (72300, False), (84100, False), (91800, True), (98450, False),
    ]
    assert datetime.fromisoformat(lecturas[2]["fecha"]) == inicio_del_dia(hoy_en_argentina() - timedelta(days=67))


def test_con_un_solo_servicio_la_frecuencia_no_se_puede_calcular(cliente, repos):
    _cargar(repos, 72300, 30)

    metricas = _metricas(cliente, repos).json()

    assert metricas["servicios"] == 1
    assert (metricas["frecuencia_km"], metricas["frecuencia_dias"], metricas["uso_km_mes"]) == (None, None, None)
    assert metricas["por_tipo"] == [{"tipo": ACEITE, "cantidad": 1}]


def test_servicios_del_mismo_dia_no_tienen_uso_mensual(cliente, repos):
    _cargar(repos, 72300, 5)
    _cargar(repos, 72310, 5, tipo="Frenos")

    metricas = _metricas(cliente, repos).json()

    assert (metricas["frecuencia_km"], metricas["frecuencia_dias"], metricas["uso_km_mes"]) == (10, 0, None)


def test_si_el_kilometraje_no_crece_no_se_calculan_promedios_en_km(cliente, repos):
    _cargar(repos, 98450, 60)
    _cargar(repos, 48100, 30)  # inconsistente: menor al anterior

    metricas = _metricas(cliente, repos).json()

    assert (metricas["frecuencia_km"], metricas["uso_km_mes"]) == (None, None)
    assert metricas["frecuencia_dias"] == 30


def test_sin_intervenciones(cliente, repos):
    metricas = _metricas(cliente, repos).json()

    assert metricas["servicios"] == 0
    assert metricas["por_tipo"] == [] and metricas["lecturas"] == []


def test_no_se_ven_las_metricas_de_un_vehiculo_ajeno(cliente, repos):
    respuesta = _metricas(cliente, repos, headers=_token(ObjectId(), Rol.PROPIETARIO))

    assert respuesta.status_code == 404
