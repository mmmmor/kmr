"""HU-005: vinculación de vehículos por dominio. Usa un repositorio en memoria."""

from datetime import UTC, datetime

import pytest
from bson import ObjectId

from app.core.seguridad import crear_token
from app.main import app
from app.modelos.usuario import Rol
from app.routers.dependencias import obtener_repositorio_vehiculos
from tests.falsos import RepositorioVehiculosFalso

PROPIETARIO_ID = str(ObjectId())
PROPIETARIO = {"Authorization": f"Bearer {crear_token(PROPIETARIO_ID, Rol.PROPIETARIO)}"}
OTRO = {"Authorization": f"Bearer {crear_token(str(ObjectId()), Rol.PROPIETARIO)}"}

DATOS_VALIDOS = {"dominio": "AE123CD", "marca": "Volkswagen", "modelo": "Gol Trend", "anio": 2020}


@pytest.fixture
def vehiculos():
    repo = RepositorioVehiculosFalso()
    app.dependency_overrides[obtener_repositorio_vehiculos] = lambda: repo
    return repo


@pytest.fixture
def vincular(cliente, vehiculos):
    def _vincular(headers=PROPIETARIO, **cambios):
        return cliente.post("/api/vehiculos", json={**DATOS_VALIDOS, **cambios}, headers=headers)

    return _vincular


# --- Vinculación ---


def test_dominio_valido_y_datos_completos_vinculan_el_vehiculo(vincular, vehiculos):
    respuesta = vincular()

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    guardado = vehiculos.vehiculos[0]
    assert cuerpo == {
        "id": str(guardado["_id"]),
        "dominio": "AE123CD",
        "marca": "Volkswagen",
        "modelo": "Gol Trend",
        "anio": 2020,
        "fecha_vinculacion": cuerpo["fecha_vinculacion"],
    }
    assert guardado["propietario_id"] == ObjectId(PROPIETARIO_ID)
    assert guardado["fecha_vinculacion"].tzinfo is not None


@pytest.mark.parametrize(
    ("ingresado", "normalizado"),
    [
        ("AE123CD", "AE123CD"),
        (" ae-123 cd ", "AE123CD"),
        ("AE 123 CD", "AE123CD"),
        ("NTR215", "NTR215"),
        ("ntr-215", "NTR215"),
        ("NTR 215", "NTR215"),
    ],
)
def test_acepta_ambos_formatos_y_guarda_el_dominio_normalizado(vincular, vehiculos, ingresado, normalizado):
    respuesta = vincular(dominio=ingresado)

    assert respuesta.status_code == 201
    assert respuesta.json()["dominio"] == normalizado
    assert vehiculos.vehiculos[0]["dominio"] == normalizado


@pytest.mark.parametrize("dominio", ["AB12CD", "ABCD123", "A1B2C3D", "AE123CDE", "123ABC", "AE.123.CD"])
def test_formato_invalido_da_error(vincular, vehiculos, dominio):
    respuesta = vincular(dominio=dominio)

    assert respuesta.status_code == 422
    assert respuesta.json()["campos"] == {
        "dominio": "El dominio no es válido: usá el formato AAA 111 o AA 111 AA."
    }
    assert vehiculos.vehiculos == []


def test_campos_incompletos_indica_cuales(vincular, vehiculos):
    respuesta = vincular(dominio="", marca=" ", modelo="", anio=None)

    assert respuesta.status_code == 422
    assert respuesta.json()["campos"] == {
        "dominio": "Completá este campo.",
        "marca": "Completá este campo.",
        "modelo": "Completá este campo.",
        "anio": "Completá este campo.",
    }


def test_anio_fuera_de_rango(vincular, vehiculos):
    maximo = datetime.now(UTC).year + 1
    mensaje = f"Ingresá un año entre 1900 y {maximo}."

    assert vincular(anio=1899).json()["campos"] == {"anio": mensaje}
    assert vincular(anio=maximo + 1).json()["campos"] == {"anio": mensaje}
    assert vincular(anio="dos mil").json()["campos"] == {"anio": "Ingresá un número entero."}
    assert vincular(anio=maximo).status_code == 201


def test_vehiculo_de_otro_propietario_da_error_sin_mas_datos(vincular, vehiculos):
    vincular(headers=OTRO)

    respuesta = vincular(dominio="ae 123 cd")

    assert respuesta.status_code == 409
    assert respuesta.json() == {
        "detail": "Ese vehículo se encuentra vinculado a otro propietario.",
        "campos": {"dominio": "Ese vehículo se encuentra vinculado a otro propietario."},
    }
    assert len(vehiculos.vehiculos) == 1
    assert vehiculos.vehiculos[0]["propietario_id"] != ObjectId(PROPIETARIO_ID)


def test_vincular_dos_veces_el_mismo_vehiculo(vincular, vehiculos):
    vincular()

    respuesta = vincular()

    assert respuesta.status_code == 409
    assert respuesta.json()["campos"] == {"dominio": "Ese vehículo ya está vinculado a tu cuenta."}
    assert len(vehiculos.vehiculos) == 1


# --- Mis vehículos ---


def test_lista_solo_los_vehiculos_propios_en_orden_de_vinculacion(cliente, vincular):
    vincular(dominio="NTR215", marca="Toyota", modelo="Etios", anio=2014)
    vincular(dominio="AF482TR", headers=OTRO)
    vincular()

    respuesta = cliente.get("/api/vehiculos", headers=PROPIETARIO)

    assert respuesta.status_code == 200
    assert [v["dominio"] for v in respuesta.json()] == ["NTR215", "AE123CD"]


def test_sin_vehiculos_devuelve_lista_vacia(cliente, vehiculos):
    assert cliente.get("/api/vehiculos", headers=PROPIETARIO).json() == []


# --- Acceso ---


@pytest.mark.parametrize("rol", [Rol.TALLER, Rol.ADMINISTRADOR])
def test_solo_el_propietario_puede_vincular_y_listar(cliente, vincular, rol):
    otro_rol = {"Authorization": f"Bearer {crear_token(str(ObjectId()), rol)}"}

    assert vincular(headers=otro_rol).status_code == 403
    assert cliente.get("/api/vehiculos", headers=otro_rol).status_code == 403
    assert cliente.post("/api/vehiculos", json=DATOS_VALIDOS).status_code == 401
    assert cliente.get("/api/vehiculos").status_code == 401
