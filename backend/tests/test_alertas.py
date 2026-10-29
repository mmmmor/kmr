"""HU-014: alertas de servicio. Usa repositorios y transacción en memoria."""

import asyncio
from datetime import timedelta

import pytest
from bson import ObjectId

from app.core.fechas import hoy_en_argentina
from app.esquemas.intervenciones import IntervencionEntrada
from app.modelos.intervencion import Origen
from app.modelos.usuario import Rol
from app.servicios import intervenciones as servicio
from tests.falsos import TransaccionFalsa
from tests.test_historial import _taller
from tests.test_intervencion_propietario import _token, repos  # noqa: F401 (fixture)

ACEITE = "Cambio de aceite y filtros"


def _fecha(dias):
    """Días desde hoy: negativo es el pasado."""
    return (hoy_en_argentina() + timedelta(days=dias)).isoformat()


def _cargar(repos, km, dias_atras, tipo=ACEITE, proxima=None, taller=None, corrige=None):
    datos = IntervencionEntrada(
        fecha_intervencion=_fecha(-dias_atras),
        kilometraje=km,
        tipo=tipo,
        items=[{"descripcion": "Filtro de aceite", "cantidad": 1}],
        proxima_revision=proxima,
    )
    intervencion = servicio.nueva(
        datos, repos.vehiculo["_id"], Origen.TALLER if taller else Origen.PROPIETARIO, ObjectId(),
        taller_id=taller["_id"] if taller else None,
    )
    if corrige is not None:
        intervencion.update(corrige_a=corrige["_id"], motivo_correccion="Error de carga.")
    return asyncio.run(
        servicio.insertar_encadenada(intervencion, repos.intervenciones, TransaccionFalsa(repos.intervenciones))
    )


def _alertas(cliente, repos, headers=None):
    return cliente.get(f"/api/vehiculos/{repos.vehiculo['_id']}/alertas", headers=headers or repos.headers)


def test_sin_proxima_revision_no_hay_alerta(cliente, repos):
    _cargar(repos, 98450, 60)

    cuerpo = _alertas(cliente, repos).json()

    assert cuerpo == {"ultimo_kilometraje": 98450, "alertas": []}


def test_lejos_de_la_fecha_y_del_kilometraje_no_hay_alerta(cliente, repos):
    _cargar(repos, 98450, 60, proxima={"kilometraje": 99450, "fecha": _fecha(30)})

    assert _alertas(cliente, repos).json()["alertas"] == []


@pytest.mark.parametrize("proxima, km_restantes, dias_restantes", [
    ({"fecha": _fecha(29)}, None, 29),  # menos de 30 días
    ({"kilometraje": 99449}, 999, None),  # menos de 1.000 km
    ({"kilometraje": 98450, "fecha": _fecha(200)}, 0, 200),  # justo en el kilometraje recomendado
])
def test_proximo(cliente, repos, proxima, km_restantes, dias_restantes):
    _cargar(repos, 97000, 60, proxima=proxima)
    _cargar(repos, 98450, 5, tipo="Frenos")  # el último kilometraje registrado

    [alerta] = _alertas(cliente, repos).json()["alertas"]

    assert alerta["estado"] == "proximo"
    assert (alerta["km_restantes"], alerta["dias_restantes"]) == (km_restantes, dias_restantes)


@pytest.mark.parametrize("proxima, km_restantes, dias_restantes", [
    ({"fecha": _fecha(-1)}, None, -1),  # la fecha ya pasó
    ({"kilometraje": 98000, "fecha": _fecha(100)}, -450, 100),  # el kilometraje ya se superó
])
def test_vencido(cliente, repos, proxima, km_restantes, dias_restantes):
    _cargar(repos, 90000, 60, tipo="Frenos")
    _cargar(repos, 97000, 30, proxima=proxima)
    _cargar(repos, 98450, 5, tipo="Frenos")  # el último kilometraje registrado lo da otro servicio

    [alerta] = _alertas(cliente, repos).json()["alertas"]

    assert alerta["estado"] == "vencido"
    assert (alerta["km_restantes"], alerta["dias_restantes"]) == (km_restantes, dias_restantes)


def test_informa_quien_la_recomendo_y_que(cliente, repos):
    taller = _taller(repos)
    servicio_con_revision = _cargar(
        repos, 98450, 60, taller=taller,
        proxima={"kilometraje": 99000, "fecha": _fecha(18), "detalle": "Frenos y tren delantero"},
    )

    [alerta] = _alertas(cliente, repos).json()["alertas"]

    assert alerta["intervencion_id"] == str(servicio_con_revision["_id"])
    assert (alerta["taller"], alerta["detalle"], alerta["tipo"]) == ("Lubricentro San Martín", "Frenos y tren delantero", ACEITE)
    assert (alerta["kilometraje"], alerta["km_restantes"], alerta["dias_restantes"]) == (99000, 550, 18)


def test_un_servicio_posterior_del_mismo_tipo_reemplaza_la_recomendacion(cliente, repos):
    _cargar(repos, 90000, 200, proxima={"kilometraje": 95000})
    _cargar(repos, 96000, 30)  # se volvió a hacer el cambio de aceite

    assert _alertas(cliente, repos).json()["alertas"] == []


def test_recomendaciones_de_distintos_tipos_vencidas_primero(cliente, repos):
    _cargar(repos, 90000, 200, tipo="Distribución", proxima={"fecha": _fecha(10)})
    _cargar(repos, 94000, 30, proxima={"kilometraje": 95500})
    _cargar(repos, 96000, 5, tipo="Frenos")

    alertas = _alertas(cliente, repos).json()["alertas"]

    assert [(a["tipo"], a["estado"]) for a in alertas] == [(ACEITE, "vencido"), ("Distribución", "proximo")]


def test_cuenta_la_proxima_revision_de_la_correccion(cliente, repos):
    original = _cargar(repos, 98450, 60, proxima={"fecha": _fecha(5)})
    _cargar(repos, 98450, 60, proxima={"fecha": _fecha(90)}, corrige=original)

    assert _alertas(cliente, repos).json()["alertas"] == []


def test_no_se_ven_las_alertas_de_un_vehiculo_ajeno(cliente, repos):
    respuesta = _alertas(cliente, repos, headers=_token(ObjectId(), Rol.PROPIETARIO))

    assert respuesta.status_code == 404
