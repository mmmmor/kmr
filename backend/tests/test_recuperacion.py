"""HU-015: recuperación de contraseña. Usa repositorios en memoria y un enviador de correos falso."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

import pytest

from app.main import app
from app.routers.dependencias import (
    obtener_repositorio_talleres,
    obtener_repositorio_tokens,
    obtener_repositorio_usuarios,
    obtener_transaccion,
)
from app.servicios.correo import obtener_enviador
from app.servicios.recuperacion import MENSAJE_SOLICITUD, hash_token
from tests.falsos import (
    EnviadorFalso,
    RepositorioTalleresFalso,
    RepositorioTokensFalso,
    RepositorioUsuariosFalso,
    TransaccionFalsa,
)

INVALIDO = "El enlace para restablecer la contraseña no es válido o ya venció."


@pytest.fixture
def repos(cliente):
    r = SimpleNamespace(
        usuarios=RepositorioUsuariosFalso(),
        tokens=RepositorioTokensFalso(),
        enviador=EnviadorFalso(),
    )
    app.dependency_overrides[obtener_repositorio_usuarios] = lambda: r.usuarios
    app.dependency_overrides[obtener_repositorio_talleres] = RepositorioTalleresFalso
    app.dependency_overrides[obtener_repositorio_tokens] = lambda: r.tokens
    app.dependency_overrides[obtener_enviador] = lambda: r.enviador
    app.dependency_overrides[obtener_transaccion] = lambda: TransaccionFalsa(r.usuarios, r.tokens)
    r.usuario = r.usuarios.agregar("lucia@correo.com", "Anterior1", nombre="Lucía")
    return r


def _recuperar(cliente, correo="lucia@correo.com"):
    return cliente.post("/api/auth/recuperar", json={"correo": correo})


def _token_enviado(repos):
    """El token que viaja en el enlace del último correo enviado."""
    enlace = next(linea for linea in repos.enviador.enviados[-1].texto.splitlines() if "token=" in linea)
    return parse_qs(urlparse(enlace).query)["token"][0]


def _restablecer(cliente, token, contrasena="Nueva1234"):
    return cliente.post("/api/auth/restablecer", json={"token": token, "contrasena": contrasena})


def _login(cliente, contrasena):
    return cliente.post("/api/auth/login", json={"correo": "lucia@correo.com", "contrasena": contrasena})


# --- Pedido del enlace ---


def test_misma_respuesta_con_correo_registrado_o_no(cliente, repos):
    registrado = _recuperar(cliente, "Lucia@Correo.com")
    no_registrado = _recuperar(cliente, "nadie@correo.com")

    assert registrado.status_code == no_registrado.status_code == 200
    assert registrado.json() == no_registrado.json() == {"mensaje": MENSAJE_SOLICITUD}
    assert [correo.destinatario for correo in repos.enviador.enviados] == ["lucia@correo.com"]


def test_envia_un_enlace_y_guarda_solo_el_hash_del_token(cliente, repos):
    _recuperar(cliente)

    correo = repos.enviador.enviados[0]
    token = _token_enviado(repos)
    assert "http://localhost:5173/recuperar?token=" in correo.texto
    assert token in correo.html
    [guardado] = repos.tokens.tokens
    assert guardado["token_hash"] == hash_token(token)
    assert token not in str(guardado), "el token en claro no se guarda"
    assert len(token) >= 40, "aleatorio y largo (secrets.token_urlsafe)"


def test_el_token_vence_a_los_30_minutos(cliente, repos):
    antes = datetime.now(UTC)
    _recuperar(cliente)

    vencimiento = repos.tokens.tokens[0]["fecha_vencimiento"]
    assert timedelta(minutes=30) <= vencimiento - antes < timedelta(minutes=30, seconds=5)


def test_pedir_un_enlace_nuevo_invalida_el_anterior(cliente, repos):
    _recuperar(cliente)
    anterior = _token_enviado(repos)
    _recuperar(cliente)

    assert _restablecer(cliente, anterior).status_code == 400
    assert _restablecer(cliente, _token_enviado(repos)).status_code == 200


def test_correo_con_formato_invalido(cliente, repos):
    respuesta = _recuperar(cliente, "lucia")

    assert respuesta.status_code == 422
    assert respuesta.json()["campos"] == {"correo": "Ingresá un correo electrónico válido."}


# --- Cambio de contraseña ---


def test_con_el_token_cambia_la_contrasena(cliente, repos):
    _recuperar(cliente)

    respuesta = _restablecer(cliente, _token_enviado(repos))

    assert respuesta.status_code == 200
    assert _login(cliente, "Nueva1234").status_code == 200
    assert _login(cliente, "Anterior1").status_code == 401


def test_el_token_es_de_un_solo_uso(cliente, repos):
    _recuperar(cliente)
    token = _token_enviado(repos)
    _restablecer(cliente, token)

    otra_vez = _restablecer(cliente, token, "Otra12345")

    assert otra_vez.status_code == 400
    assert otra_vez.json()["detail"] == INVALIDO
    assert _login(cliente, "Nueva1234").status_code == 200


def test_un_token_vencido_no_sirve(cliente, repos):
    _recuperar(cliente)
    repos.tokens.tokens[0]["fecha_vencimiento"] = datetime.now(UTC) - timedelta(seconds=1)

    respuesta = _restablecer(cliente, _token_enviado(repos))

    assert respuesta.status_code == 400
    assert _login(cliente, "Anterior1").status_code == 200, "la contraseña no cambió"


def test_un_token_inventado_no_sirve(cliente, repos):
    assert _restablecer(cliente, "no-existe").json()["detail"] == INVALIDO


def test_la_nueva_contrasena_cumple_la_politica_y_no_consume_el_token(cliente, repos):
    _recuperar(cliente)
    token = _token_enviado(repos)

    respuesta = _restablecer(cliente, token, "corta")

    assert respuesta.status_code == 422
    assert "contrasena" in respuesta.json()["campos"]
    assert _restablecer(cliente, token).status_code == 200, "el token sigue sirviendo"


def test_restablecer_levanta_el_bloqueo_por_intentos(cliente, repos):
    repos.usuario.update(bloqueado_hasta=datetime.now(UTC) + timedelta(minutes=10), intentos_login_fallidos=0)
    _recuperar(cliente)

    _restablecer(cliente, _token_enviado(repos))

    assert _login(cliente, "Nueva1234").status_code == 200
