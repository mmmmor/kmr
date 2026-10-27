"""Tests contra un MongoDB real. Solo corren si está definida MONGODB_URI_TEST (en CI, el service del workflow)."""

import os

import pytest
from fastapi.testclient import TestClient
from pymongo import MongoClient

from app.core.config import obtener_settings
from app.main import app

URI_TEST = os.environ.get("MONGODB_URI_TEST")
BASE_TEST = "kmr_test"

pytestmark = pytest.mark.skipif(
    not URI_TEST, reason="sin MONGODB_URI_TEST: se omiten los tests contra MongoDB"
)


@pytest.fixture
def cliente_con_base(monkeypatch):
    monkeypatch.setenv("MONGODB_URI", URI_TEST)
    monkeypatch.setenv("MONGODB_DB", BASE_TEST)
    obtener_settings.cache_clear()
    with MongoClient(URI_TEST) as cliente_sync:
        cliente_sync.drop_database(BASE_TEST)
    # Con "with" corre el lifespan, que abre la conexión real y crea los índices.
    with TestClient(app) as cliente:
        yield cliente
    obtener_settings.cache_clear()


def test_salud_con_mongodb_real(cliente_con_base):
    respuesta = cliente_con_base.get("/api/salud")

    assert respuesta.status_code == 200
    assert respuesta.json() == {"api": "ok", "base_de_datos": "ok"}


def test_registro_guarda_en_mongodb_y_el_indice_rechaza_el_correo_repetido(cliente_con_base):
    datos = {"nombre": "Diego", "apellido": "Paz", "correo": "diego@correo.com", "contrasena": "Clave1234"}

    alta = cliente_con_base.post("/api/auth/registro", json=datos)
    repetido = cliente_con_base.post("/api/auth/registro", json={**datos, "correo": "Diego@Correo.com"})

    assert alta.status_code == 201
    assert repetido.status_code == 409
    with MongoClient(URI_TEST) as cliente_sync:
        usuarios = list(cliente_sync[BASE_TEST]["usuarios"].find())
    assert len(usuarios) == 1
    assert usuarios[0]["rol"] == "propietario"
    assert usuarios[0]["contrasena_hash"].startswith("$2b$")


def test_login_y_bloqueo_con_mongodb_real(cliente_con_base):
    datos = {"nombre": "Diego", "apellido": "Paz", "correo": "diego@correo.com", "contrasena": "Clave1234"}
    cliente_con_base.post("/api/auth/registro", json=datos)

    def login(contrasena):
        return cliente_con_base.post("/api/auth/login", json={"correo": "diego@correo.com", "contrasena": contrasena})

    assert login("Clave1234").status_code == 200
    respuestas = [login("mala").status_code for _ in range(5)]
    assert respuestas == [401, 401, 401, 401, 429]
    assert login("Clave1234").status_code == 429

    with MongoClient(URI_TEST) as cliente_sync:
        usuario = cliente_sync[BASE_TEST]["usuarios"].find_one({"correo": "diego@correo.com"})
    assert usuario["bloqueado_hasta"] is not None
    assert usuario["intentos_login_fallidos"] == 0


def test_solicitud_de_taller_con_cuit_repetido_revierte_la_transaccion(cliente_con_base):
    datos = {
        "nombre": "Diego", "apellido": "Paz", "correo": "taller1@correo.com", "contrasena": "Clave1234",
        "razon_social": "Taller Los Álamos", "cuit": "30-71589234-7",
        "domicilio": "Av. Colón 1543", "telefono": "351 555-0142",
    }

    alta = cliente_con_base.post("/api/talleres/solicitud", json=datos)
    repetido = cliente_con_base.post("/api/talleres/solicitud", json={**datos, "correo": "taller2@correo.com"})

    assert alta.status_code == 201
    assert repetido.status_code == 409
    assert repetido.json()["campos"] == {"cuit": "Ya hay un taller registrado con ese CUIT."}
    with MongoClient(URI_TEST) as cliente_sync:
        base = cliente_sync[BASE_TEST]
        assert base["usuarios"].count_documents({}) == 1, "quedó un usuario sin solicitud"
        assert base["usuarios"].find_one({"correo": "taller2@correo.com"}) is None
        taller = base["talleres"].find_one()
    assert taller["estado_solicitud"] == "pendiente"
    assert taller["cuit"] == "30715892347"


def test_mongodb_es_replica_set_y_admite_transacciones():
    with MongoClient(URI_TEST, serverSelectionTimeoutMS=5000) as cliente:
        assert cliente.admin.command("hello").get("setName"), "MongoDB no corre como replica set"

        base = cliente[BASE_TEST]
        base.drop_collection("prueba_transacciones")
        coleccion = base.create_collection("prueba_transacciones")

        with cliente.start_session() as sesion:
            with sesion.start_transaction():
                coleccion.insert_one({"valor": 1}, session=sesion)

        assert coleccion.count_documents({}) == 1
        base.drop_collection("prueba_transacciones")
