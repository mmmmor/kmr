from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt
import pytest
from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.core.config import obtener_settings
from app.core.seguridad import (
    UsuarioSesion,
    crear_token,
    decodificar_token,
    hashear_contrasena,
    requiere_rol,
    validar_politica_contrasena,
    verificar_contrasena,
)
from app.modelos.usuario import Rol

# --- Política de contraseñas ---


@pytest.mark.parametrize("contrasena", ["Clave123", "MiAuto2026!", "A1" + "x" * 62])
def test_contrasenas_validas(contrasena):
    assert validar_politica_contrasena(contrasena) is None


@pytest.mark.parametrize(
    ("contrasena", "esperado"),
    [
        ("Ab1", "La contraseña debe tener al menos 8 caracteres."),
        ("clave1234", "La contraseña debe tener al menos una mayúscula."),
        ("ClaveSegura", "La contraseña debe tener al menos un número."),
        ("clave", "La contraseña debe tener al menos 8 caracteres, al menos una mayúscula y al menos un número."),
        ("A1" + "x" * 63, "La contraseña no puede superar los 64 caracteres."),
    ],
)
def test_contrasenas_invalidas_informan_el_requisito(contrasena, esperado):
    assert validar_politica_contrasena(contrasena) == esperado


def test_contrasena_que_supera_72_bytes_se_rechaza():
    contrasena = "A1" + "ñ" * 40  # 42 caracteres, 82 bytes en UTF-8

    assert "demasiado larga" in validar_politica_contrasena(contrasena)


# --- Hash bcrypt ---


def test_hash_no_guarda_la_contrasena_y_se_verifica():
    contrasena_hash = hashear_contrasena("Clave123")

    assert "Clave123" not in contrasena_hash
    assert contrasena_hash.startswith("$2b$")
    assert verificar_contrasena("Clave123", contrasena_hash)
    assert not verificar_contrasena("Clave124", contrasena_hash)


def test_cada_hash_usa_un_salt_distinto():
    assert hashear_contrasena("Clave123") != hashear_contrasena("Clave123")


def test_verificar_con_hash_corrupto_devuelve_false():
    assert not verificar_contrasena("Clave123", "no-es-un-hash")


# --- JWT ---


def test_token_lleva_usuario_y_rol_y_vence_a_las_2_horas():
    token = crear_token("abc123", Rol.PROPIETARIO)

    sesion = decodificar_token(token)
    payload = jwt.decode(token, options={"verify_signature": False})

    assert sesion == UsuarioSesion(id="abc123", rol=Rol.PROPIETARIO)
    assert payload["exp"] - payload["iat"] == 120 * 60


def test_token_vencido_se_rechaza():
    ahora = datetime.now(UTC)
    token = jwt.encode(
        {"sub": "abc123", "rol": "propietario", "iat": ahora - timedelta(hours=3), "exp": ahora - timedelta(hours=1)},
        obtener_settings().jwt_secret,
        algorithm="HS256",
    )

    with pytest.raises(HTTPException) as error:
        decodificar_token(token)
    assert error.value.status_code == 401


def test_token_firmado_con_otra_clave_se_rechaza():
    token = jwt.encode(
        {"sub": "abc123", "rol": "administrador", "exp": datetime.now(UTC) + timedelta(hours=1)},
        "otra-clave-cualquiera-de-al-menos-32-caracteres",
        algorithm="HS256",
    )

    with pytest.raises(HTTPException) as error:
        decodificar_token(token)
    assert error.value.status_code == 401


def test_token_sin_firma_se_rechaza():
    token = jwt.encode(
        {"sub": "abc123", "rol": "administrador", "exp": datetime.now(UTC) + timedelta(hours=1)},
        None,
        algorithm="none",
    )

    with pytest.raises(HTTPException):
        decodificar_token(token)


# --- requiere_rol ---

app_prueba = FastAPI()


@app_prueba.get("/solo-propietarios")
def solo_propietarios(usuario: Annotated[UsuarioSesion, Depends(requiere_rol(Rol.PROPIETARIO))]):
    return {"id": usuario.id}


cliente_prueba = TestClient(app_prueba)


def _auth(rol: Rol) -> dict:
    return {"Authorization": f"Bearer {crear_token('abc123', rol)}"}


def test_requiere_rol_deja_pasar_al_rol_correcto():
    respuesta = cliente_prueba.get("/solo-propietarios", headers=_auth(Rol.PROPIETARIO))

    assert respuesta.status_code == 200
    assert respuesta.json() == {"id": "abc123"}


def test_requiere_rol_rechaza_otro_rol():
    respuesta = cliente_prueba.get("/solo-propietarios", headers=_auth(Rol.TALLER))

    assert respuesta.status_code == 403
    assert respuesta.json()["detail"] == "No tenés permiso para realizar esta acción."


def test_requiere_rol_sin_token_pide_iniciar_sesion():
    respuesta = cliente_prueba.get("/solo-propietarios")

    assert respuesta.status_code == 401
    assert respuesta.json()["detail"] == "Iniciá sesión para continuar."


def test_requiere_rol_con_token_invalido():
    respuesta = cliente_prueba.get("/solo-propietarios", headers={"Authorization": "Bearer basura"})

    assert respuesta.status_code == 401
