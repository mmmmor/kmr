"""Tests contra un MongoDB real. Solo corren si está definida MONGODB_URI_TEST (en CI, el service del workflow)."""

import asyncio
import json
import os
from datetime import timedelta

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient
from pymongo import AsyncMongoClient, MongoClient
from pymongo.errors import DuplicateKeyError

from app.core.config import obtener_settings
from app.core.fechas import hoy_en_argentina
from app.core.seguridad import crear_token
from app.main import app
from app.modelos.usuario import Rol
from app.repositorios.codigos import RepositorioCodigos
from app.servicios import codigos as servicio_codigos
from app.servicios.hash import verificar_cadena

URI_TEST = os.environ.get("MONGODB_URI_TEST")
BASE_TEST = "kmr_test"

pytestmark = pytest.mark.skipif(
    not URI_TEST, reason="sin MONGODB_URI_TEST: se omiten los tests contra MongoDB"
)


def _con_codigos(funcion):
    """Corre `funcion(repositorio)` sobre la base de test, con un cliente async propio de este hilo."""

    async def correr():
        cliente = AsyncMongoClient(URI_TEST, tz_aware=True)
        try:
            return await funcion(RepositorioCodigos(cliente[BASE_TEST]))
        finally:
            await cliente.close()

    return asyncio.run(correr())


def _propietario_con_vehiculo(cliente):
    propietario = {"Authorization": f"Bearer {crear_token(str(ObjectId()), Rol.PROPIETARIO)}"}
    datos = {"dominio": "AE123CD", "marca": "Volkswagen", "modelo": "Gol Trend", "anio": 2020}
    vehiculo = cliente.post("/api/vehiculos", json=datos, headers=propietario).json()
    return propietario, vehiculo


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


def test_admin_lista_con_responsable_y_aprueba_con_mongodb_real(cliente_con_base):
    admin ={"Authorization": f"Bearer {crear_token(str(ObjectId()), Rol.ADMINISTRADOR)}"}
    datos = {
        "nombre": "Diego", "apellido": "Paz", "correo": "taller@correo.com", "contrasena": "Clave1234",
        "razon_social": "Taller Los Álamos", "cuit": "30715892347",
        "domicilio": "Av. Colón 1543", "telefono": "351 555-0142",
    }
    cliente_con_base.post("/api/talleres/solicitud", json=datos)

    pendientes = cliente_con_base.get("/api/admin/solicitudes", headers=admin).json()
    assert len(pendientes) == 1
    assert pendientes[0]["responsable"] == {"nombre": "Diego", "apellido": "Paz", "correo": "taller@correo.com"}

    aprobar = cliente_con_base.post(f"/api/admin/solicitudes/{pendientes[0]['id']}/aprobar", headers=admin)
    login = cliente_con_base.post("/api/auth/login", json={"correo": "taller@correo.com", "contrasena": "Clave1234"})

    assert aprobar.status_code == 204
    assert login.status_code == 200
    assert cliente_con_base.get("/api/admin/solicitudes", headers=admin).json() == []


def test_el_indice_unico_impide_vincular_un_dominio_a_dos_propietarios(cliente_con_base):
    uno, otro =(
        {"Authorization": f"Bearer {crear_token(str(ObjectId()), Rol.PROPIETARIO)}"} for _ in range(2)
    )
    datos = {"dominio": "AE123CD", "marca": "Volkswagen", "modelo": "Gol Trend", "anio": 2020}

    alta = cliente_con_base.post("/api/vehiculos", json=datos, headers=uno)
    repetido = cliente_con_base.post("/api/vehiculos", json={**datos, "dominio": "ae-123 cd"}, headers=otro)

    assert alta.status_code == 201
    assert repetido.status_code == 409
    assert repetido.json()["detail"] == "Ese vehículo se encuentra vinculado a otro propietario."
    assert [v["dominio"] for v in cliente_con_base.get("/api/vehiculos", headers=uno).json()] == ["AE123CD"]
    assert cliente_con_base.get("/api/vehiculos", headers=otro).json() == []


def test_generar_codigo_invalida_el_anterior_en_una_transaccion(cliente_con_base):
    propietario, vehiculo = _propietario_con_vehiculo(cliente_con_base)
    ruta = f"/api/vehiculos/{vehiculo['id']}/codigos"

    primero = cliente_con_base.post(ruta, headers=propietario).json()
    segundo = cliente_con_base.post(ruta, headers=propietario).json()
    listado = cliente_con_base.get(ruta, headers=propietario).json()

    assert listado["vigente"]["id"] == segundo["id"]
    assert [(c["id"], c["estado"]) for c in listado["anteriores"]] == [(primero["id"], "invalidado")]


def test_uso_unico_del_codigo_con_mongodb_real(cliente_con_base):
    propietario, vehiculo = _propietario_con_vehiculo(cliente_con_base)
    ruta = f"/api/vehiculos/{vehiculo['id']}/codigos"
    codigo = cliente_con_base.post(ruta, headers=propietario).json()["codigo"]
    taller_id = ObjectId()
    with MongoClient(URI_TEST) as cliente_sync:
        cliente_sync[BASE_TEST]["talleres"].insert_one({"_id": taller_id, "razon_social": "Lubricentro San Martín"})

    async def usar_dos_veces(codigos):
        vigente = await servicio_codigos.validar(ObjectId(vehiculo["id"]), codigo, codigos)
        await servicio_codigos.consumir(vigente, taller_id, codigos)
        with pytest.raises(servicio_codigos.CodigoInvalido):
            await servicio_codigos.consumir(vigente, taller_id, codigos)
        with pytest.raises(servicio_codigos.CodigoInvalido):
            await servicio_codigos.validar(ObjectId(vehiculo["id"]), codigo, codigos)

    _con_codigos(usar_dos_veces)

    usado = cliente_con_base.get(ruta, headers=propietario).json()["anteriores"][0]
    assert usado["estado"] == "utilizado"
    assert usado["taller"] == "Lubricentro San Martín"


def test_el_sexto_intento_fallido_invalida_el_codigo_con_mongodb_real(cliente_con_base):
    propietario, vehiculo = _propietario_con_vehiculo(cliente_con_base)
    ruta = f"/api/vehiculos/{vehiculo['id']}/codigos"
    codigo = cliente_con_base.post(ruta, headers=propietario).json()["codigo"]
    incorrecto = f"{(int(codigo) + 1) % 10**6:06d}"

    def fallar(veces):
        async def intentar(codigos):
            for _ in range(veces):
                with pytest.raises(servicio_codigos.CodigoInvalido):
                    await servicio_codigos.validar(ObjectId(vehiculo["id"]), incorrecto, codigos)

        return intentar

    _con_codigos(fallar(5))
    con_cinco = cliente_con_base.get(ruta, headers=propietario).json()
    _con_codigos(fallar(1))
    con_seis = cliente_con_base.get(ruta, headers=propietario).json()

    assert con_cinco["vigente"]["intentos_fallidos"] == 5
    assert con_seis["vigente"] is None
    assert (con_seis["anteriores"][0]["estado"], con_seis["anteriores"][0]["intentos_fallidos"]) == ("invalidado", 6)


def _taller_aprobado(cliente):
    """Solicitud de taller aprobada por un administrador. Devuelve los headers de sesión del taller."""
    admin = {"Authorization": f"Bearer {crear_token(str(ObjectId()), Rol.ADMINISTRADOR)}"}
    cliente.post("/api/talleres/solicitud", json={
        "nombre": "Sergio", "apellido": "Molina", "correo": "taller@correo.com", "contrasena": "Clave1234",
        "razon_social": "Lubricentro San Martín", "cuit": "30715892347",
        "domicilio": "Av. San Martín 1234", "telefono": "351 555-0142",
    })
    solicitud = cliente.get("/api/admin/solicitudes", headers=admin).json()[0]
    cliente.post(f"/api/admin/solicitudes/{solicitud['id']}/aprobar", headers=admin)
    sesion = cliente.post("/api/auth/login", json={"correo": "taller@correo.com", "contrasena": "Clave1234"}).json()
    assert sesion["razon_social"] == "Lubricentro San Martín"
    return {"Authorization": f"Bearer {sesion['token']}"}


def test_registro_del_taller_con_mongodb_real(cliente_con_base):
    pdf = b"%PDF-1.7\n% comprobante de prueba\n"
    taller = _taller_aprobado(cliente_con_base)
    propietario, vehiculo = _propietario_con_vehiculo(cliente_con_base)
    ayer = (hoy_en_argentina() - timedelta(days=1)).isoformat()

    def registrar(kilometraje, archivo=None):
        codigo = cliente_con_base.post(f"/api/vehiculos/{vehiculo['id']}/codigos", headers=propietario).json()
        autorizacion = cliente_con_base.post(
            "/api/taller/autorizacion", json={"dominio": "AE 123 CD", "codigo": codigo["codigo"]}, headers=taller
        )
        assert autorizacion.status_code == 200
        datos = {
            "dominio": "AE123CD", "codigo": codigo["codigo"], "fecha_intervencion": ayer, "kilometraje": kilometraje,
            "tipo": "Frenos", "items": [{"descripcion": "Disco de freno delantero", "cantidad": 2}],
        }
        return cliente_con_base.post(
            "/api/taller/intervenciones",
            data={"datos": json.dumps(datos)},
            files={"comprobante": archivo} if archivo else None,
            headers=taller,
        )

    primera = registrar(98450, ("factura.pdf", pdf, "application/pdf"))
    segunda = registrar(100210)

    assert (primera.status_code, segunda.status_code) == (201, 201)
    with MongoClient(URI_TEST, tz_aware=True) as cliente_sync:
        base = cliente_sync[BASE_TEST]
        guardadas = list(base["intervenciones"].find({"vehiculo_id": ObjectId(vehiculo["id"])}).sort("fecha_registro", 1))
        # El hash recalculado desde lo que devuelve MongoDB coincide con el calculado al insertar.
        assert verificar_cadena(guardadas)
        assert guardadas[1]["hash_anterior"] == guardadas[0]["hash"]
        with pytest.raises(DuplicateKeyError):
            base["intervenciones"].insert_one({**guardadas[1], "_id": ObjectId()})
        assert base["codigos_autorizacion"].count_documents({"estado": "utilizado"}) == 2

    descarga = cliente_con_base.get(f"/api/intervenciones/{primera.json()['id']}/comprobante", headers=propietario)
    assert (descarga.status_code, descarga.content) == (200, pdf)
    registros = cliente_con_base.get("/api/taller/intervenciones", headers=taller).json()
    assert [(r["kilometraje"], r["dominio"]) for r in registros] == [(100210, "AE123CD"), (98450, "AE123CD")]


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
