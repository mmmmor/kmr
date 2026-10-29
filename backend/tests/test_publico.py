"""HU-010: consulta pública por dominio, sin cuenta y sin datos personales del titular."""

import json

import pytest

from tests.test_correcciones import _cargar, _corregir, repos  # noqa: F401 (fixture)

# Claves que nunca pueden aparecer en la respuesta pública.
PROHIBIDAS = {
    "nombre", "apellido", "correo", "propietario", "propietario_id", "usuario_id", "registrado_por",
    "codigo_id", "comprobante_id", "hash", "hash_anterior", "fecha_vinculacion",
}


def _claves(valor):
    if isinstance(valor, dict):
        return set(valor) | {c for v in valor.values() for c in _claves(v)}
    if isinstance(valor, list):
        return {c for v in valor for c in _claves(v)}
    return set()


def _consultar(cliente, dominio="AE123CD"):
    return cliente.get(f"/api/publico/vehiculos/{dominio}")


def test_no_requiere_cuenta_y_devuelve_el_historial(cliente, repos):
    _cargar(repos, 84100, 200)
    _cargar(repos, 98450, 70, taller=repos.taller)

    respuesta = _consultar(cliente, "ae-123 cd")

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["dominio"] == "AE123CD"
    assert cuerpo["vehiculo"] == {"dominio": "AE123CD", "marca": "Volkswagen", "modelo": "Gol Trend", "anio": 2020}
    assert cuerpo["integridad_verificada"] is True
    assert cuerpo["ultima_lectura"]["kilometraje"] == 98450
    del_taller, autorreportada = cuerpo["intervenciones"]
    assert (del_taller["origen"], del_taller["taller"]) == ("taller", "Lubricentro San Martín")
    assert (autorreportada["origen"], autorreportada["taller"]) == ("propietario", None)
    assert del_taller["items"] == [{"descripcion": "Juego de pastillas de freno delanteras", "cantidad": 1}]
    assert del_taller["tiene_comprobante"] is False


def test_la_respuesta_no_contiene_ningun_dato_personal_del_propietario(cliente, repos):
    _cargar(repos, 84100, 200)
    original = _cargar(repos, 48100, 70, taller=repos.taller)
    _corregir(cliente, original, repos.headers_taller, kilometraje=91800)

    respuesta = _consultar(cliente)

    cuerpo = respuesta.json()
    assert _claves(cuerpo).isdisjoint(PROHIBIDAS)
    # La descripción libre del registro no (los ítems sí tienen la suya: es el nombre del insumo).
    assert all("descripcion" not in intervencion for intervencion in cuerpo["intervenciones"])
    texto = json.dumps(cuerpo)
    assert str(repos.propietario_id) not in texto
    assert str(repos.taller["usuario_id"]) not in texto, "ni quién cargó cada registro"
    assert "Cambio de pastillas delanteras." not in texto, "la descripción libre puede tener datos personales"


def test_muestra_correcciones_vinculadas_y_alertas(cliente, repos):
    _cargar(repos, 84100, 200, taller=repos.taller)
    original = _cargar(repos, 48100, 70, taller=repos.taller)
    _corregir(cliente, original, repos.headers_taller, kilometraje=91800)

    correccion, corregido, _ = _consultar(cliente).json()["intervenciones"]

    assert correccion["corrige_a"]["id"] == corregido["id"]
    assert correccion["motivo_correccion"] == "Error de tipeo en el kilometraje."
    assert corregido["corregido_por"]["id"] == correccion["id"]
    assert corregido["alerta_kilometraje"]["tipo"] == "kilometraje_inferior"
    assert corregido["alerta_kilometraje"]["kilometraje_anterior"] == 84100


@pytest.mark.parametrize("dominio", ["AB123CD", "NTR215"])
def test_sin_intervenciones_no_revela_si_el_dominio_tiene_cuenta(cliente, repos, dominio):
    # AE123CD está vinculado pero sin registros en este test; AB123CD y NTR215 no existen.
    vinculado_sin_registros = _consultar(cliente, "AE123CD").json()
    inexistente = _consultar(cliente, dominio).json()

    for cuerpo in (vinculado_sin_registros, inexistente):
        assert cuerpo["vehiculo"] is None
        assert cuerpo["intervenciones"] == []
    assert {**vinculado_sin_registros, "dominio": dominio} == inexistente


def test_informa_si_la_cadena_fue_alterada(cliente, repos):
    _cargar(repos, 84100, 200)
    _cargar(repos, 98450, 70)
    repos.intervenciones.intervenciones[0]["kilometraje"] = 50000

    assert _consultar(cliente).json()["integridad_verificada"] is False


@pytest.mark.parametrize("dominio", ["AE12", "1234567", "AE-123-CDX"])
def test_dominio_con_formato_invalido(cliente, repos, dominio):
    respuesta = _consultar(cliente, dominio)

    assert respuesta.status_code == 422
    assert respuesta.json()["campos"] == {
        "dominio": "El dominio no es válido: usá el formato AAA 111 o AA 111 AA."
    }
