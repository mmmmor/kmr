"""HU-009: validación del kilometraje. Nunca se rechaza un registro: se guarda con la alerta."""

from datetime import date, datetime, timedelta

import pytest
from bson import ObjectId

from app.core.fechas import hoy_en_argentina, inicio_del_dia
from app.modelos.intervencion import AlertaKilometraje
from app.servicios import kilometraje
from app.servicios.hash import verificar_cadena
from tests.test_intervencion_propietario import _registrar, repos  # noqa: F401 (fixture)

INFERIOR = AlertaKilometraje.KILOMETRAJE_INFERIOR
INCOMPATIBLE = AlertaKilometraje.INCREMENTO_INCOMPATIBLE
BASE = date(2026, 8, 14)
_orden = iter(range(1, 10**6))


def _lectura(km, dia=BASE, corrige_a=None):
    """Registro mínimo para las funciones de kilometraje; se cargan en el orden en que se crean."""
    return {
        "_id": ObjectId(),
        "kilometraje": km,
        "fecha_intervencion": inicio_del_dia(dia),
        "fecha_registro": datetime(2026, 10, 1) + timedelta(seconds=next(_orden)),
        "corrige_a": corrige_a,
    }


def _evaluar(km, dias_despues, referencia=_lectura(98450)):
    fecha = inicio_del_dia(BASE + timedelta(days=dias_despues))
    return kilometraje.evaluar(km, fecha, referencia, km_max_por_dia=500)


# --- Reglas ---


def test_la_primera_intervencion_no_se_valida():
    assert kilometraje.evaluar(5, inicio_del_dia(BASE), None, km_max_por_dia=500) is None


def test_kilometraje_menor_al_ultimo_registrado():
    assert _evaluar(98449, 30) is INFERIOR


def test_mismo_kilometraje_es_coherente():
    assert _evaluar(98450, 30) is None


@pytest.mark.parametrize("km, dias, alerta", [
    (98450 + 500 * 30, 30, None),               # justo el máximo: 500 km por día
    (98450 + 500 * 30 + 1, 30, INCOMPATIBLE),   # un km más
    (98450 + 500, 0, None),                     # el mismo día admite hasta un día de uso
    (98450 + 501, 0, INCOMPATIBLE),
    (98450 + 1, -1, INCOMPATIBLE),              # servicio anterior a la última lectura con más km
])
def test_incremento_compatible_con_el_tiempo_transcurrido(km, dias, alerta):
    assert _evaluar(km, dias) is alerta


def test_el_maximo_por_dia_es_configurable():
    fecha = inicio_del_dia(BASE + timedelta(days=10))
    referencia = _lectura(98450)

    assert kilometraje.evaluar(98450 + 3000, fecha, referencia, km_max_por_dia=500) is None
    assert kilometraje.evaluar(98450 + 3000, fecha, referencia, km_max_por_dia=200) is INCOMPATIBLE


# --- Última lectura válida ---


def test_la_ultima_lectura_es_la_del_servicio_mas_reciente_no_la_ultima_cargada():
    reciente = _lectura(99870, BASE + timedelta(days=20))
    cargada_despues = _lectura(98450, BASE)

    assert kilometraje.ultima_lectura([reciente, cargada_despues]) is reciente


def test_si_un_registro_fue_corregido_cuenta_la_correccion():
    anterior = _lectura(84100, BASE - timedelta(days=60))
    con_error = _lectura(48100, BASE)
    correccion = _lectura(91800, BASE, corrige_a=con_error["_id"])
    registros = [anterior, con_error, correccion]

    assert kilometraje.lecturas_validas(registros) == [anterior, correccion]
    assert kilometraje.ultima_lectura(registros) is correccion


def test_una_correccion_se_compara_con_lo_anterior_al_registro_que_corrige():
    anterior = _lectura(84100, BASE - timedelta(days=60))
    con_error = _lectura(948100, BASE)
    correccion = _lectura(91800, BASE, corrige_a=con_error["_id"])

    assert kilometraje.lectura_de_referencia([anterior, con_error], correccion) is anterior


def test_reconstruye_la_lectura_contra_la_que_se_valido_cada_registro():
    primero = _lectura(84100, BASE - timedelta(days=60))
    segundo = _lectura(98450, BASE)
    tercero = _lectura(90000, BASE + timedelta(days=30))

    assert kilometraje.referencias([primero, segundo, tercero]) == {
        primero["_id"]: None,
        segundo["_id"]: primero,
        tercero["_id"]: segundo,
    }


# --- Al registrar ---


def _fecha(dias_atras):
    return (hoy_en_argentina() - timedelta(days=dias_atras)).isoformat()


def test_un_kilometraje_inferior_se_guarda_igual_con_la_alerta(cliente, repos):
    _registrar(cliente, repos, kilometraje=98450, fecha_intervencion=_fecha(40))

    respuesta = _registrar(cliente, repos, kilometraje=48100, fecha_intervencion=_fecha(10))

    assert respuesta.status_code == 201, "una alerta nunca rechaza el registro"
    alerta = respuesta.json()["alerta_kilometraje"]
    assert alerta["tipo"] == "kilometraje_inferior"
    assert alerta["kilometraje_anterior"] == 98450
    assert datetime.fromisoformat(alerta["fecha_anterior"]) == inicio_del_dia(hoy_en_argentina() - timedelta(days=40))
    guardada = repos.intervenciones.intervenciones[-1]
    assert guardada["alerta_kilometraje"] == "kilometraje_inferior"
    assert verificar_cadena(repos.intervenciones.intervenciones), "la alerta forma parte del registro hasheado"


def test_un_incremento_incompatible_se_guarda_igual_con_la_alerta(cliente, repos):
    _registrar(cliente, repos, kilometraje=98450, fecha_intervencion=_fecha(10))

    respuesta = _registrar(cliente, repos, kilometraje=98450 + 500 * 7 + 1, fecha_intervencion=_fecha(3))

    assert respuesta.status_code == 201
    assert respuesta.json()["alerta_kilometraje"]["tipo"] == "incremento_incompatible"


def test_un_kilometraje_coherente_no_tiene_alerta(cliente, repos):
    _registrar(cliente, repos, kilometraje=98450, fecha_intervencion=_fecha(40))

    respuesta = _registrar(cliente, repos, kilometraje=100210, fecha_intervencion=_fecha(10))

    assert respuesta.json()["alerta_kilometraje"] is None
    assert repos.intervenciones.intervenciones[-1]["alerta_kilometraje"] is None


def test_la_primera_intervencion_del_vehiculo_no_tiene_alerta(cliente, repos):
    respuesta = _registrar(cliente, repos, kilometraje=3)

    assert respuesta.status_code == 201
    assert respuesta.json()["alerta_kilometraje"] is None
