"""HU-002: inicio de sesión. Usa repositorios en memoria en lugar de MongoDB."""

from datetime import UTC, datetime, timedelta

import pytest

from app.core.seguridad import decodificar_token
from app.main import app
from app.modelos.usuario import Rol
from app.routers.dependencias import obtener_repositorio_talleres, obtener_repositorio_usuarios
from tests.falsos import RepositorioTalleresFalso, RepositorioUsuariosFalso

CORREO = "diego.paz@correo.com"
CONTRASENA = "Clave1234"
GENERICO = "Usuario o contraseña incorrectos."


@pytest.fixture
def usuarios():
    repo = RepositorioUsuariosFalso()
    app.dependency_overrides[obtener_repositorio_usuarios] = lambda: repo
    return repo


@pytest.fixture
def talleres():
    repo = RepositorioTalleresFalso()
    app.dependency_overrides[obtener_repositorio_talleres] = lambda: repo
    return repo


@pytest.fixture
def login(cliente, usuarios, talleres):
    def _login(correo=CORREO, contrasena=CONTRASENA):
        return cliente.post("/api/auth/login", json={"correo": correo, "contrasena": contrasena})

    return _login


# --- Credenciales ---


def test_credenciales_correctas_devuelven_token_y_rol(login, usuarios):
    usuario = usuarios.agregar(CORREO, CONTRASENA)

    respuesta = login()

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["rol"] == "propietario"
    assert cuerpo["nombre"] == "Diego"
    assert cuerpo["apellido"] == "Paz"
    sesion = decodificar_token(cuerpo["token"])
    assert sesion.id == usuario["_id"]
    assert sesion.rol is Rol.PROPIETARIO


def test_el_correo_no_distingue_mayusculas(login, usuarios):
    usuarios.agregar(CORREO, CONTRASENA)

    assert login(correo="  Diego.Paz@CORREO.com ").status_code == 200


def test_contrasena_incorrecta_da_mensaje_generico(login, usuarios):
    usuarios.agregar(CORREO, CONTRASENA)

    respuesta = login(contrasena="Clave9999")

    assert respuesta.status_code == 401
    assert respuesta.json() == {"detail": GENERICO}


def test_correo_inexistente_da_el_mismo_mensaje_generico(login, usuarios):
    usuarios.agregar(CORREO, CONTRASENA)

    con_correo_inexistente = login(correo="nadie@correo.com")
    con_contrasena_incorrecta = login(contrasena="Clave9999")

    assert con_correo_inexistente.status_code == con_contrasena_incorrecta.status_code == 401
    assert con_correo_inexistente.json() == con_contrasena_incorrecta.json()


def test_campos_vacios_no_continua(login, usuarios):
    respuesta = login(correo=" ", contrasena="")

    assert respuesta.status_code == 422
    assert respuesta.json()["campos"] == {
        "correo": "Completá este campo.",
        "contrasena": "Completá este campo.",
    }


@pytest.mark.parametrize("rol", ["propietario", "administrador"])
def test_cada_rol_recibe_su_rol(login, usuarios, rol):
    usuarios.agregar(CORREO, CONTRASENA, rol=rol)

    assert login().json()["rol"] == rol


# --- Bloqueo por intentos fallidos ---


def test_cuatro_fallos_y_luego_correcto_ingresa_y_reinicia_el_contador(login, usuarios):
    usuario = usuarios.agregar(CORREO, CONTRASENA)
    for _ in range(4):
        assert login(contrasena="mala").status_code == 401

    assert login().status_code == 200
    assert usuario["intentos_login_fallidos"] == 0


def test_cinco_fallos_bloquean_la_cuenta_15_minutos(login, usuarios):
    usuario = usuarios.agregar(CORREO, CONTRASENA)
    for _ in range(4):
        login(contrasena="mala")

    quinto = login(contrasena="mala")

    assert quinto.status_code == 429
    assert quinto.json()["detail"] == (
        "Tu cuenta quedó bloqueada por demasiados intentos fallidos. Probá de nuevo en 15 minutos."
    )
    restante = usuario["bloqueado_hasta"] - datetime.now(UTC)
    assert timedelta(minutes=14) < restante <= timedelta(minutes=15)


def test_cuenta_bloqueada_rechaza_incluso_la_contrasena_correcta(login, usuarios):
    usuarios.agregar(CORREO, CONTRASENA)
    for _ in range(5):
        login(contrasena="mala")

    respuesta = login()

    assert respuesta.status_code == 429
    assert "bloqueada" in respuesta.json()["detail"]


def test_vencido_el_bloqueo_se_puede_ingresar(login, usuarios):
    usuario = usuarios.agregar(CORREO, CONTRASENA)
    usuario["bloqueado_hasta"] = datetime.now(UTC) - timedelta(seconds=1)

    respuesta = login()

    assert respuesta.status_code == 200
    assert usuario["bloqueado_hasta"] is None


def test_los_fallos_no_consecutivos_no_bloquean(login, usuarios):
    usuarios.agregar(CORREO, CONTRASENA)
    for _ in range(4):
        login(contrasena="mala")
    login()
    for _ in range(4):
        login(contrasena="mala")

    assert login().status_code == 200


# --- Talleres ---


def test_taller_pendiente_no_puede_ingresar(login, usuarios, talleres):
    usuario = usuarios.agregar(CORREO, CONTRASENA, rol="taller")
    talleres.talleres.append({"usuario_id": usuario["_id"], "estado_solicitud": "pendiente"})

    respuesta = login()

    assert respuesta.status_code == 403
    assert "pendiente de revisión" in respuesta.json()["detail"]
    assert "token" not in respuesta.json()


def test_taller_rechazado_informa_el_motivo(login, usuarios, talleres):
    usuario = usuarios.agregar(CORREO, CONTRASENA, rol="taller")
    talleres.talleres.append(
        {"usuario_id": usuario["_id"], "estado_solicitud": "rechazado", "motivo_rechazo": "El CUIT no coincide con ARCA."}
    )

    respuesta = login()

    assert respuesta.status_code == 403
    assert respuesta.json()["detail"] == (
        "Tu solicitud de alta como taller fue rechazada. Motivo: El CUIT no coincide con ARCA."
    )


def test_taller_aprobado_ingresa(login, usuarios, talleres):
    usuario = usuarios.agregar(CORREO, CONTRASENA, rol="taller")
    talleres.talleres.append(
        {"usuario_id": usuario["_id"], "estado_solicitud": "aprobado", "razon_social": "Lubricentro San Martín"}
    )

    respuesta = login()

    assert respuesta.status_code == 200
    assert respuesta.json()["rol"] == "taller"
    assert respuesta.json()["razon_social"] == "Lubricentro San Martín"


def test_taller_con_contrasena_incorrecta_recibe_el_mensaje_generico(login, usuarios, talleres):
    usuario = usuarios.agregar(CORREO, CONTRASENA, rol="taller")
    talleres.talleres.append({"usuario_id": usuario["_id"], "estado_solicitud": "pendiente"})

    respuesta = login(contrasena="mala")

    assert respuesta.status_code == 401
    assert respuesta.json() == {"detail": GENERICO}
