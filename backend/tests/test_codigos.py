"""HU-006: código temporal de autorización. Usa repositorios y transacción en memoria.

La validación del código por parte del taller (HU-007) se prueba acá a nivel de servicio,
porque los intentos fallidos y el uso único son reglas del código.
"""

import asyncio
import re
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from bson import ObjectId

from app.core.seguridad import crear_token
from app.main import app
from app.modelos.usuario import Rol
from app.routers.dependencias import (
    obtener_repositorio_codigos,
    obtener_repositorio_vehiculos,
    obtener_transaccion,
)
from app.servicios import codigos as servicio_codigos
from app.servicios.codigos import CodigoInvalido
from tests.falsos import (
    RepositorioCodigosFalso,
    RepositorioTalleresFalso,
    RepositorioVehiculosFalso,
    TransaccionFalsa,
)

PROPIETARIO_ID = str(ObjectId())
PROPIETARIO = {"Authorization": f"Bearer {crear_token(PROPIETARIO_ID, Rol.PROPIETARIO)}"}


@pytest.fixture
def repos(cliente):
    vehiculos, codigos, talleres = RepositorioVehiculosFalso(), RepositorioCodigosFalso(), RepositorioTalleresFalso()
    codigos.talleres = talleres
    transaccion = TransaccionFalsa(codigos)
    app.dependency_overrides[obtener_repositorio_vehiculos] = lambda: vehiculos
    app.dependency_overrides[obtener_repositorio_codigos] = lambda: codigos
    app.dependency_overrides[obtener_transaccion] = lambda: transaccion
    vehiculo = {
        "_id": ObjectId(),
        "dominio": "AE123CD",
        "marca": "Volkswagen",
        "modelo": "Gol Trend",
        "anio": 2020,
        "propietario_id": ObjectId(PROPIETARIO_ID),
        "fecha_vinculacion": datetime.now(UTC),
    }
    vehiculos.vehiculos.append(vehiculo)
    return SimpleNamespace(vehiculos=vehiculos, codigos=codigos, talleres=talleres, vehiculo=vehiculo)


def _generar(cliente, repos, headers=PROPIETARIO):
    return cliente.post(f"/api/vehiculos/{repos.vehiculo['_id']}/codigos", headers=headers)


def _listar(cliente, repos, headers=PROPIETARIO):
    return cliente.get(f"/api/vehiculos/{repos.vehiculo['_id']}/codigos", headers=headers)


def _validar(repos, ingresado, ahora=None):
    return asyncio.run(servicio_codigos.validar(repos.vehiculo["_id"], ingresado, repos.codigos, ahora))


def _incorrecto(codigo: str) -> str:
    return f"{(int(codigo) + 1) % 10**6:06d}"


# --- Generación ---


def test_genera_un_codigo_de_6_digitos_que_vence_a_las_24_horas(cliente, repos):
    respuesta = _generar(cliente, repos)

    assert respuesta.status_code == 201
    codigo = respuesta.json()
    assert re.fullmatch(r"\d{6}", codigo["codigo"])
    assert codigo["estado"] == "vigente"
    assert codigo["intentos_fallidos"] == 0
    assert codigo["taller"] is None
    guardado = repos.codigos.codigos[0]
    assert guardado["fecha_vencimiento"] - guardado["fecha_generacion"] == timedelta(hours=24)
    assert guardado["vehiculo_id"] == repos.vehiculo["_id"]
    assert guardado["fecha_generacion"].tzinfo is not None


def test_los_digitos_se_completan_con_ceros(monkeypatch):
    monkeypatch.setattr(servicio_codigos.secrets, "randbelow", lambda limite: 42)

    assert servicio_codigos.generar_digitos() == "000042"


def test_generar_uno_nuevo_invalida_el_anterior(cliente, repos, monkeypatch):
    digitos = iter(["111111", "222222"])
    monkeypatch.setattr(servicio_codigos, "generar_digitos", lambda: next(digitos))
    primero = _generar(cliente, repos).json()
    segundo = _generar(cliente, repos).json()

    listado = _listar(cliente, repos).json()

    assert listado["vigente"]["id"] == segundo["id"]
    assert [(c["id"], c["estado"]) for c in listado["anteriores"]] == [(primero["id"], "invalidado")]
    assert listado["max_intentos_fallidos"] == 5
    with pytest.raises(CodigoInvalido):
        _validar(repos, "111111")
    assert _validar(repos, "222222")["intentos_fallidos"] == 1, "el ingreso del código viejo cuenta como fallido"


def test_sin_codigos_no_hay_vigente_ni_anteriores(cliente, repos):
    assert _listar(cliente, repos).json() == {"vigente": None, "anteriores": [], "max_intentos_fallidos": 5}


# --- Vencimiento ---


def test_a_las_24_horas_el_codigo_vence(cliente, repos):
    codigo = _generar(cliente, repos).json()["codigo"]
    despues = datetime.now(UTC) + timedelta(hours=24, seconds=1)

    with pytest.raises(CodigoInvalido):
        _validar(repos, codigo, ahora=despues)
    assert _validar(repos, codigo, ahora=datetime.now(UTC) + timedelta(hours=23, minutes=59))


def test_un_codigo_vencido_se_lista_como_vencido_y_no_se_invalida_al_generar_otro(cliente, repos):
    hace_25_horas = datetime.now(UTC) - timedelta(hours=25)
    asyncio.run(servicio_codigos.generar(repos.vehiculo, repos.codigos, TransaccionFalsa(), ahora=hace_25_horas))

    antes = _listar(cliente, repos).json()
    _generar(cliente, repos)
    despues = _listar(cliente, repos).json()

    assert antes["vigente"] is None
    assert [c["estado"] for c in antes["anteriores"]] == ["vencido"]
    assert [c["estado"] for c in despues["anteriores"]] == ["vencido"]
    assert repos.codigos.codigos[0]["estado"] == "vigente", "vencido no se guarda: se calcula"


# --- Uso único ---


def test_el_codigo_se_usa_una_sola_vez(cliente, repos):
    repos.talleres.talleres.append({"_id": (taller_id := ObjectId()), "razon_social": "Lubricentro San Martín"})
    codigo = _generar(cliente, repos).json()["codigo"]

    vigente = _validar(repos, codigo)
    asyncio.run(servicio_codigos.consumir(vigente, taller_id, repos.codigos))

    with pytest.raises(CodigoInvalido):
        _validar(repos, codigo)
    usado = _listar(cliente, repos).json()["anteriores"][0]
    assert usado["estado"] == "utilizado"
    assert usado["taller"] == "Lubricentro San Martín"
    assert usado["fecha_uso"] is not None
    assert repos.codigos.codigos[0]["taller_id"] == taller_id


def test_dos_cargas_simultaneas_no_pueden_consumir_el_mismo_codigo(cliente, repos):
    codigo = _generar(cliente, repos).json()["codigo"]
    primera, segunda = _validar(repos, codigo), _validar(repos, codigo)

    asyncio.run(servicio_codigos.consumir(primera, ObjectId(), repos.codigos))
    with pytest.raises(CodigoInvalido):
        asyncio.run(servicio_codigos.consumir(segunda, ObjectId(), repos.codigos))


# --- Intentos fallidos ---


def test_cada_intento_fallido_suma_al_codigo_vigente(cliente, repos):
    codigo = _generar(cliente, repos).json()["codigo"]

    for _ in range(2):
        with pytest.raises(CodigoInvalido):
            _validar(repos, _incorrecto(codigo))

    assert _listar(cliente, repos).json()["vigente"]["intentos_fallidos"] == 2


def test_con_cinco_intentos_fallidos_el_codigo_sigue_sirviendo(cliente, repos):
    codigo = _generar(cliente, repos).json()["codigo"]
    for _ in range(5):
        with pytest.raises(CodigoInvalido):
            _validar(repos, _incorrecto(codigo))

    assert _listar(cliente, repos).json()["vigente"]["intentos_fallidos"] == 5
    assert _validar(repos, codigo)["codigo"] == codigo


def test_el_sexto_intento_fallido_invalida_el_codigo(cliente, repos):
    codigo = _generar(cliente, repos).json()["codigo"]
    for _ in range(6):
        with pytest.raises(CodigoInvalido):
            _validar(repos, _incorrecto(codigo))

    listado = _listar(cliente, repos).json()
    assert listado["vigente"] is None
    assert listado["anteriores"][0]["estado"] == "invalidado"
    assert listado["anteriores"][0]["intentos_fallidos"] == 6
    with pytest.raises(CodigoInvalido):
        _validar(repos, codigo)


def test_sin_codigo_vigente_cualquier_ingreso_es_invalido(cliente, repos):
    with pytest.raises(CodigoInvalido):
        _validar(repos, "123456")


# --- Acceso ---


def test_solo_el_propietario_del_vehiculo_ve_y_genera_sus_codigos(cliente, repos):
    otro = {"Authorization": f"Bearer {crear_token(str(ObjectId()), Rol.PROPIETARIO)}"}

    for respuesta in (_generar(cliente, repos, otro), _listar(cliente, repos, otro)):
        assert respuesta.status_code == 404
        assert respuesta.json()["detail"] == "El vehículo no está vinculado a tu cuenta."
    assert repos.codigos.codigos == []


@pytest.mark.parametrize("vehiculo_id", [str(ObjectId()), "no-es-un-id"])
def test_vehiculo_inexistente(cliente, repos, vehiculo_id):
    assert cliente.post(f"/api/vehiculos/{vehiculo_id}/codigos", headers=PROPIETARIO).status_code == 404


@pytest.mark.parametrize("rol", [Rol.TALLER, Rol.ADMINISTRADOR])
def test_otros_roles_no_pueden_generar_codigos(cliente, repos, rol):
    otro_rol = {"Authorization": f"Bearer {crear_token(str(ObjectId()), rol)}"}

    assert _generar(cliente, repos, otro_rol).status_code == 403
    assert _listar(cliente, repos, otro_rol).status_code == 403
    assert cliente.get(f"/api/vehiculos/{repos.vehiculo['_id']}/codigos").status_code == 401
