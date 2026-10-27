"""HU-001: registro de propietario. Usa un repositorio en memoria en lugar de MongoDB."""

import pytest

from app.core.seguridad import verificar_contrasena
from app.main import app
from app.routers.dependencias import obtener_repositorio_usuarios
from tests.falsos import RepositorioUsuariosFalso


@pytest.fixture
def repo():
    repo = RepositorioUsuariosFalso()
    app.dependency_overrides[obtener_repositorio_usuarios] = lambda: repo
    return repo


DATOS_VALIDOS = {
    "nombre": "Diego",
    "apellido": "Paz",
    "correo": "diego.paz@correo.com",
    "contrasena": "Clave1234",
}


def test_alta_correcta_crea_un_propietario(cliente, repo):
    respuesta = cliente.post("/api/auth/registro", json=DATOS_VALIDOS)

    assert respuesta.status_code == 201
    assert respuesta.json() == {
        "id": "id1",
        "nombre": "Diego",
        "apellido": "Paz",
        "correo": "diego.paz@correo.com",
        "rol": "propietario",
    }
    guardado = repo.usuarios[0]
    assert guardado["rol"] == "propietario"
    assert guardado["intentos_login_fallidos"] == 0
    assert guardado["bloqueado_hasta"] is None
    assert guardado["fecha_alta"].tzinfo is not None


def test_la_contrasena_se_guarda_solo_como_hash(cliente, repo):
    respuesta = cliente.post("/api/auth/registro", json=DATOS_VALIDOS)

    guardado = repo.usuarios[0]
    assert "contrasena" not in guardado
    assert guardado["contrasena_hash"] != "Clave1234"
    assert verificar_contrasena("Clave1234", guardado["contrasena_hash"])
    assert "contrasena" not in respuesta.text and "hash" not in respuesta.text


def test_correo_se_normaliza_a_minusculas_y_sin_espacios(cliente, repo):
    cliente.post("/api/auth/registro", json={**DATOS_VALIDOS, "correo": "  Diego.Paz@Correo.COM "})

    assert repo.usuarios[0]["correo"] == "diego.paz@correo.com"


def test_correo_repetido_da_error(cliente, repo):
    cliente.post("/api/auth/registro", json=DATOS_VALIDOS)

    respuesta = cliente.post(
        "/api/auth/registro", json={**DATOS_VALIDOS, "nombre": "Otro", "correo": "DIEGO.PAZ@correo.com"}
    )

    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == "Ya existe una cuenta con ese correo electrónico."
    assert len(repo.usuarios) == 1


def test_contrasena_invalida_informa_la_restriccion(cliente, repo):
    respuesta = cliente.post("/api/auth/registro", json={**DATOS_VALIDOS, "contrasena": "clave1234"})

    assert respuesta.status_code == 422
    assert respuesta.json()["campos"] == {"contrasena": "La contraseña debe tener al menos una mayúscula."}
    assert repo.usuarios == []


def test_campos_incompletos_indica_cuales(cliente, repo):
    respuesta = cliente.post("/api/auth/registro", json={"nombre": "Diego", "apellido": "   ", "contrasena": ""})

    assert respuesta.status_code == 422
    assert respuesta.json() == {
        "detail": "Revisá los datos ingresados.",
        "campos": {
            "apellido": "Completá este campo.",
            "correo": "Completá este campo.",
            "contrasena": "Completá este campo.",
        },
    }
    assert repo.usuarios == []


def test_correo_con_formato_invalido(cliente, repo):
    respuesta = cliente.post("/api/auth/registro", json={**DATOS_VALIDOS, "correo": "diego.paz"})

    assert respuesta.status_code == 422
    assert respuesta.json()["campos"] == {"correo": "Ingresá un correo electrónico válido."}


def test_no_se_puede_elegir_el_rol(cliente, repo):
    respuesta = cliente.post("/api/auth/registro", json={**DATOS_VALIDOS, "rol": "administrador"})

    assert respuesta.status_code == 201
    assert repo.usuarios[0]["rol"] == "propietario"
