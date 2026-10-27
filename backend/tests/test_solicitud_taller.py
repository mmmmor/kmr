"""HU-003: solicitud de alta de taller. Usa repositorios y transacción en memoria."""

import pytest

from app.core.seguridad import verificar_contrasena
from app.esquemas.talleres import digito_verificador_cuit
from app.main import app
from app.routers.dependencias import (
    obtener_repositorio_talleres,
    obtener_repositorio_usuarios,
    obtener_transaccion,
)
from tests.falsos import RepositorioTalleresFalso, RepositorioUsuariosFalso, TransaccionFalsa

DATOS_VALIDOS = {
    "nombre": "Diego",
    "apellido": "Paz",
    "correo": "diego.paz@correo.com",
    "contrasena": "Clave1234",
    "razon_social": "Taller Mecánico Los Álamos",
    "cuit": "30-71589234-7",
    "domicilio": "Av. Colón 1543, Córdoba",
    "telefono": "351 555-0142",
}


@pytest.fixture
def repos():
    usuarios, talleres = RepositorioUsuariosFalso(), RepositorioTalleresFalso()
    transaccion = TransaccionFalsa(usuarios, talleres)
    app.dependency_overrides[obtener_repositorio_usuarios] = lambda: usuarios
    app.dependency_overrides[obtener_repositorio_talleres] = lambda: talleres
    app.dependency_overrides[obtener_transaccion] = lambda: transaccion
    return usuarios, talleres


@pytest.fixture
def solicitar(cliente, repos):
    def _solicitar(**cambios):
        return cliente.post("/api/talleres/solicitud", json={**DATOS_VALIDOS, **cambios})

    return _solicitar


def test_solicitud_completa_queda_pendiente(solicitar, repos):
    usuarios, talleres = repos

    respuesta = solicitar()

    assert respuesta.status_code == 201
    assert respuesta.json() == {
        "id": "taller1",
        "razon_social": "Taller Mecánico Los Álamos",
        "cuit": "30715892347",
        "estado_solicitud": "pendiente",
    }
    usuario, taller = usuarios.usuarios[0], talleres.talleres[0]
    assert usuario["rol"] == "taller"
    assert verificar_contrasena("Clave1234", usuario["contrasena_hash"])
    assert taller["usuario_id"] == usuario["_id"]
    assert taller["estado_solicitud"] == "pendiente"
    assert taller["motivo_rechazo"] is None
    assert taller["aprobado_por"] is None
    assert taller["fecha_resolucion"] is None
    assert taller["fecha_solicitud"].tzinfo is not None


def test_cuit_repetido_da_error_y_no_deja_un_usuario_huerfano(solicitar, repos):
    usuarios, talleres = repos
    solicitar()

    respuesta = solicitar(correo="otro@correo.com", cuit="30715892347")

    assert respuesta.status_code == 409
    assert respuesta.json()["campos"] == {"cuit": "Ya hay un taller registrado con ese CUIT."}
    assert [u["correo"] for u in usuarios.usuarios] == ["diego.paz@correo.com"]
    assert len(talleres.talleres) == 1


def test_correo_repetido_da_error_y_no_crea_el_taller(solicitar, repos):
    usuarios, talleres = repos
    usuarios.agregar("diego.paz@correo.com", "Clave1234")

    respuesta = solicitar()

    assert respuesta.status_code == 409
    assert respuesta.json()["campos"] == {"correo": "Ya existe una cuenta con ese correo electrónico."}
    assert talleres.talleres == []


def test_campos_incompletos_indica_cuales(solicitar, repos):
    respuesta = solicitar(razon_social=" ", cuit="", domicilio="", telefono="")

    assert respuesta.status_code == 422
    assert respuesta.json()["campos"] == {
        "razon_social": "Completá este campo.",
        "cuit": "Completá este campo.",
        "domicilio": "Completá este campo.",
        "telefono": "Completá este campo.",
    }
    assert repos[0].usuarios == []


def test_tambien_valida_los_datos_personales(solicitar, repos):
    respuesta = solicitar(nombre="", contrasena="corta")

    assert respuesta.status_code == 422
    assert set(respuesta.json()["campos"]) == {"nombre", "contrasena"}


@pytest.mark.parametrize("cuit", ["30715892347", "30-71589234-7", " 30 71589234 7 ", "20-12345678-6"])
def test_cuits_validos_se_guardan_como_11_digitos(solicitar, repos, cuit):
    respuesta = solicitar(cuit=cuit)

    assert respuesta.status_code == 201
    assert respuesta.json()["cuit"] == cuit.replace("-", "").replace(" ", "")


@pytest.mark.parametrize(
    ("cuit", "mensaje"),
    [
        ("30-7158923-7", "El CUIT debe tener 11 dígitos (por ejemplo, 30-71589234-7)."),
        ("30-71589234-AB", "El CUIT debe tener 11 dígitos (por ejemplo, 30-71589234-7)."),
        ("30-71589234-8", "El CUIT no es válido: revisá los números ingresados."),
    ],
)
def test_cuit_invalido(solicitar, repos, cuit, mensaje):
    respuesta = solicitar(cuit=cuit)

    assert respuesta.status_code == 422
    assert respuesta.json()["campos"] == {"cuit": mensaje}


@pytest.mark.parametrize("telefono", ["351 555-0142", "+54 9 (351) 555-0142", "4555555"])
def test_telefonos_validos(solicitar, repos, telefono):
    assert solicitar(telefono=telefono).status_code == 201


@pytest.mark.parametrize("telefono", ["12345", "351-abc-0142", "+54 9 351 555 0142 1234"])
def test_telefonos_invalidos(solicitar, repos, telefono):
    respuesta = solicitar(telefono=telefono)

    assert respuesta.status_code == 422
    assert respuesta.json()["campos"] == {"telefono": "Ingresá un teléfono válido."}


def test_la_cuenta_pendiente_no_puede_usarse(solicitar, cliente, repos):
    solicitar()

    login = cliente.post("/api/auth/login", json={"correo": "diego.paz@correo.com", "contrasena": "Clave1234"})

    assert login.status_code == 403
    assert "pendiente de revisión" in login.json()["detail"]


def test_digito_verificador():
    assert digito_verificador_cuit("3071589234") == 7
    assert digito_verificador_cuit("2012345678") == 6
