"""HU-004: aprobación de talleres. Usa repositorios y transacción en memoria."""

import pytest
from bson import ObjectId

from app.core.seguridad import crear_token
from app.main import app
from app.modelos.usuario import Rol
from app.routers.dependencias import (
    obtener_repositorio_talleres,
    obtener_repositorio_usuarios,
    obtener_transaccion,
)
from tests.falsos import RepositorioTalleresFalso, RepositorioUsuariosFalso, TransaccionFalsa

ADMIN_ID = str(ObjectId())
ADMIN = {"Authorization": f"Bearer {crear_token(ADMIN_ID, Rol.ADMINISTRADOR)}"}


def _solicitud(n: int, cuit: str) -> dict:
    return {
        "nombre": "Diego", "apellido": f"Paz{n}", "correo": f"taller{n}@correo.com", "contrasena": "Clave1234",
        "razon_social": f"Taller {n}", "cuit": cuit, "domicilio": "Av. Colón 1543", "telefono": "351 555-0142",
    }


@pytest.fixture
def talleres(cliente):
    usuarios, talleres = RepositorioUsuariosFalso(), RepositorioTalleresFalso()
    talleres.usuarios = usuarios
    transaccion = TransaccionFalsa(usuarios, talleres)
    app.dependency_overrides[obtener_repositorio_usuarios] = lambda: usuarios
    app.dependency_overrides[obtener_repositorio_talleres] = lambda: talleres
    app.dependency_overrides[obtener_transaccion] = lambda: transaccion
    for n, cuit in [(1, "30715892347"), (2, "20123456786")]:
        assert cliente.post("/api/talleres/solicitud", json=_solicitud(n, cuit)).status_code == 201
    return talleres


def _pendientes(cliente):
    return cliente.get("/api/admin/solicitudes?estado=pendiente", headers=ADMIN)


def _login(cliente, n):
    return cliente.post("/api/auth/login", json={"correo": f"taller{n}@correo.com", "contrasena": "Clave1234"})


# --- Listado ---


def test_lista_las_pendientes_con_sus_datos_mas_reciente_primero(cliente, talleres):
    respuesta = _pendientes(cliente)

    assert respuesta.status_code == 200
    solicitudes = respuesta.json()
    assert [s["razon_social"] for s in solicitudes] == ["Taller 2", "Taller 1"]
    primera = solicitudes[1]
    assert primera["cuit"] == "30715892347"
    assert primera["domicilio"] == "Av. Colón 1543"
    assert primera["telefono"] == "351 555-0142"
    assert primera["estado_solicitud"] == "pendiente"
    assert primera["responsable"] == {"nombre": "Diego", "apellido": "Paz1", "correo": "taller1@correo.com"}
    assert "contrasena_hash" not in respuesta.text


def test_sin_solicitudes_devuelve_lista_vacia(cliente, talleres):
    talleres.talleres.clear()

    assert _pendientes(cliente).json() == []


def test_estado_por_defecto_es_pendiente(cliente, talleres):
    assert len(cliente.get("/api/admin/solicitudes", headers=ADMIN).json()) == 2


# --- Aprobar ---


def test_aprobar_habilita_el_login_del_taller(cliente, talleres):
    solicitud_id = _pendientes(cliente).json()[1]["id"]
    assert _login(cliente, 1).status_code == 403

    respuesta = cliente.post(f"/api/admin/solicitudes/{solicitud_id}/aprobar", headers=ADMIN)

    assert respuesta.status_code == 204
    taller = talleres.talleres[0]
    assert taller["estado_solicitud"] == "aprobado"
    assert taller["aprobado_por"] == ObjectId(ADMIN_ID)
    assert taller["fecha_resolucion"] is not None
    assert _login(cliente, 1).status_code == 200
    assert [s["razon_social"] for s in _pendientes(cliente).json()] == ["Taller 2"]
    aprobadas = cliente.get("/api/admin/solicitudes?estado=aprobado", headers=ADMIN).json()
    assert [s["razon_social"] for s in aprobadas] == ["Taller 1"]


# --- Rechazar ---


def test_rechazar_guarda_el_motivo_y_el_taller_lo_ve_al_ingresar(cliente, talleres):
    solicitud_id = _pendientes(cliente).json()[1]["id"]

    respuesta = cliente.post(
        f"/api/admin/solicitudes/{solicitud_id}/rechazar",
        json={"motivo": "  La razón social no coincide con ARCA.  "},
        headers=ADMIN,
    )

    assert respuesta.status_code == 204
    assert talleres.talleres[0]["estado_solicitud"] == "rechazado"
    assert talleres.talleres[0]["motivo_rechazo"] == "La razón social no coincide con ARCA."
    login = _login(cliente, 1)
    assert login.status_code == 403
    assert login.json()["detail"].endswith("Motivo: La razón social no coincide con ARCA.")


@pytest.mark.parametrize("cuerpo", [{}, {"motivo": ""}, {"motivo": "   "}])
def test_rechazar_exige_motivo(cliente, talleres, cuerpo):
    solicitud_id = _pendientes(cliente).json()[0]["id"]

    respuesta = cliente.post(f"/api/admin/solicitudes/{solicitud_id}/rechazar", json=cuerpo, headers=ADMIN)

    assert respuesta.status_code == 422
    assert respuesta.json()["campos"] == {"motivo": "Completá este campo."}
    assert all(t["estado_solicitud"] == "pendiente" for t in talleres.talleres)


# --- Casos límite ---


def test_no_se_puede_resolver_dos_veces(cliente, talleres):
    solicitud_id = _pendientes(cliente).json()[0]["id"]
    cliente.post(f"/api/admin/solicitudes/{solicitud_id}/aprobar", headers=ADMIN)

    respuesta = cliente.post(
        f"/api/admin/solicitudes/{solicitud_id}/rechazar", json={"motivo": "Cambio de idea"}, headers=ADMIN
    )

    assert respuesta.status_code == 409
    assert talleres.talleres[1]["estado_solicitud"] == "aprobado"


@pytest.mark.parametrize("solicitud_id", [str(ObjectId()), "no-es-un-id"])
def test_solicitud_inexistente(cliente, talleres, solicitud_id):
    respuesta = cliente.post(f"/api/admin/solicitudes/{solicitud_id}/aprobar", headers=ADMIN)

    assert respuesta.status_code == 404
    assert respuesta.json()["detail"] == "La solicitud no existe."


@pytest.mark.parametrize("rol", [Rol.PROPIETARIO, Rol.TALLER])
def test_solo_el_administrador_puede_usar_estos_endpoints(cliente, talleres, rol):
    otro = {"Authorization": f"Bearer {crear_token(str(ObjectId()), rol)}"}
    solicitud_id = _pendientes(cliente).json()[0]["id"]

    assert cliente.get("/api/admin/solicitudes", headers=otro).status_code == 403
    assert cliente.post(f"/api/admin/solicitudes/{solicitud_id}/aprobar", headers=otro).status_code == 403
    assert cliente.get("/api/admin/solicitudes").status_code == 401
