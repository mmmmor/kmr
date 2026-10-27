"""HU-007: registro de intervenciones por el taller. Usa repositorios y transacción en memoria."""

import asyncio
import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from bson import ObjectId

from app.core.fechas import hoy_en_argentina, inicio_del_dia
from app.core.seguridad import crear_token
from app.main import app
from app.modelos.usuario import Rol
from app.routers.dependencias import (
    obtener_almacen_comprobantes,
    obtener_repositorio_codigos,
    obtener_repositorio_intervenciones,
    obtener_repositorio_talleres,
    obtener_repositorio_vehiculos,
    obtener_transaccion,
)
from app.servicios import codigos as servicio_codigos
from app.servicios.hash import verificar_cadena
from tests.falsos import (
    AlmacenComprobantesFalso,
    RepositorioCodigosFalso,
    RepositorioIntervencionesFalso,
    RepositorioTalleresFalso,
    RepositorioVehiculosFalso,
    TransaccionFalsa,
)

CODIGO_INVALIDO = "Código de autorización inválido o vencido."
PDF = b"%PDF-1.7\n% comprobante de prueba\n"


def _token(usuario_id, rol):
    return {"Authorization": f"Bearer {crear_token(str(usuario_id), rol)}"}


def _taller(talleres, razon_social, estado="aprobado"):
    usuario_id = ObjectId()
    taller = {"_id": ObjectId(), "usuario_id": usuario_id, "razon_social": razon_social, "estado_solicitud": estado}
    talleres.talleres.append(taller)
    return taller, _token(usuario_id, Rol.TALLER)


@pytest.fixture
def repos(cliente):
    r = SimpleNamespace(
        talleres=RepositorioTalleresFalso(),
        vehiculos=RepositorioVehiculosFalso(),
        codigos=RepositorioCodigosFalso(),
        intervenciones=RepositorioIntervencionesFalso(),
        comprobantes=AlmacenComprobantesFalso(),
    )
    r.codigos.talleres = r.talleres
    r.intervenciones.vehiculos = r.vehiculos
    transaccion = TransaccionFalsa(r.codigos, r.intervenciones)
    app.dependency_overrides[obtener_repositorio_talleres] = lambda: r.talleres
    app.dependency_overrides[obtener_repositorio_vehiculos] = lambda: r.vehiculos
    app.dependency_overrides[obtener_repositorio_codigos] = lambda: r.codigos
    app.dependency_overrides[obtener_repositorio_intervenciones] = lambda: r.intervenciones
    app.dependency_overrides[obtener_almacen_comprobantes] = lambda: r.comprobantes
    app.dependency_overrides[obtener_transaccion] = lambda: transaccion

    r.propietario_id = ObjectId()
    r.vehiculo = {
        "_id": ObjectId(), "dominio": "AE123CD", "marca": "Volkswagen", "modelo": "Gol Trend", "anio": 2020,
        "propietario_id": r.propietario_id, "fecha_vinculacion": datetime.now(UTC),
    }
    r.vehiculos.vehiculos.append(r.vehiculo)
    r.taller, r.headers = _taller(r.talleres, "Lubricentro San Martín")
    r.codigo = _generar_codigo(r)
    return r


def _generar_codigo(repos) -> str:
    salida = asyncio.run(servicio_codigos.generar(repos.vehiculo, repos.codigos, TransaccionFalsa(repos.codigos)))
    return salida.codigo


def _incorrecto(codigo):
    return f"{(int(codigo) + 1) % 10**6:06d}"


def _datos(repos, **cambios):
    ayer = hoy_en_argentina() - timedelta(days=1)
    return {
        "dominio": "ae 123 cd",
        "codigo": repos.codigo,
        "fecha_intervencion": ayer.isoformat(),
        "kilometraje": 100210,
        "tipo": "Frenos",
        "descripcion": "Revisión de frenos y tren delantero.",
        "items": [
            {"descripcion": "Disco de freno delantero", "cantidad": 2},
            {"descripcion": "Alineación y balanceo", "cantidad": 1},
        ],
        "proxima_revision": {"kilometraje": 110000, "fecha": None, "detalle": "Cambio de aceite y filtros"},
        **cambios,
    }


def _registrar(cliente, repos, headers=None, archivo=None, **cambios):
    archivos = {"comprobante": archivo} if archivo else None
    return cliente.post(
        "/api/taller/intervenciones",
        data={"datos": json.dumps(_datos(repos, **cambios))},
        files=archivos,
        headers=headers or repos.headers,
    )


def _autorizar(cliente, repos, headers=None, **cambios):
    cuerpo = {"dominio": "AE123CD", "codigo": repos.codigo, **cambios}
    return cliente.post("/api/taller/autorizacion", json=cuerpo, headers=headers or repos.headers)


# --- Paso 1: autorización ---


def test_dominio_y_codigo_validos_habilitan_el_formulario_sin_consumir_el_codigo(cliente, repos):
    respuesta = _autorizar(cliente, repos, dominio="ae-123 cd")

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "dominio": "AE123CD", "marca": "Volkswagen", "modelo": "Gol Trend", "anio": 2020, "ultima_lectura": None,
    }
    assert repos.codigos.codigos[0]["estado"] == "vigente"


def test_la_autorizacion_informa_el_ultimo_kilometraje(cliente, repos):
    _registrar(cliente, repos)
    repos.codigo = _generar_codigo(repos)

    ultima = _autorizar(cliente, repos).json()["ultima_lectura"]

    assert ultima["kilometraje"] == 100210
    ayer = hoy_en_argentina() - timedelta(days=1)
    assert datetime.fromisoformat(ultima["fecha"]) == inicio_del_dia(ayer)


@pytest.mark.parametrize(
    "cambios",
    [
        lambda repos: {"codigo": _incorrecto(repos.codigo)},
        lambda repos: {"dominio": "NTR215"},  # sin vincular: no se revela que no tiene cuenta
    ],
    ids=["codigo_incorrecto", "dominio_sin_vincular"],
)
def test_codigo_incorrecto_o_dominio_sin_vincular_dan_el_mismo_error(cliente, repos, cambios):
    respuesta = _autorizar(cliente, repos, **cambios(repos))

    assert respuesta.status_code == 403
    assert respuesta.json() == {"detail": CODIGO_INVALIDO, "campos": {"codigo": CODIGO_INVALIDO}}


def test_un_codigo_incorrecto_suma_un_intento_fallido(cliente, repos):
    _autorizar(cliente, repos, codigo=_incorrecto(repos.codigo))

    assert repos.codigos.codigos[0]["intentos_fallidos"] == 1


def test_codigo_vencido(cliente, repos):
    repos.codigos.codigos[0]["fecha_vencimiento"] = datetime.now(UTC) - timedelta(minutes=1)

    assert _autorizar(cliente, repos).json()["detail"] == CODIGO_INVALIDO


@pytest.mark.parametrize(("codigo", "mensaje"), [("", "Completá este campo."), ("12345", "El código tiene 6 dígitos.")])
def test_formato_del_codigo(cliente, repos, codigo, mensaje):
    respuesta = _autorizar(cliente, repos, codigo=codigo)

    assert respuesta.status_code == 422
    assert respuesta.json()["campos"] == {"codigo": mensaje}


# --- Paso 2: registro ---


def test_datos_completos_registran_la_intervencion_con_el_taller_y_la_fecha_de_carga(cliente, repos):
    respuesta = _registrar(cliente, repos)

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    guardada = repos.intervenciones.intervenciones[0]
    assert cuerpo["id"] == str(guardada["_id"])
    assert cuerpo["dominio"] == "AE123CD"
    assert cuerpo["origen"] == "taller"
    assert cuerpo["kilometraje"] == 100210
    assert cuerpo["items"] == [
        {"descripcion": "Disco de freno delantero", "cantidad": 2},
        {"descripcion": "Alineación y balanceo", "cantidad": 1},
    ]
    assert cuerpo["proxima_revision"] == {"kilometraje": 110000, "fecha": None, "detalle": "Cambio de aceite y filtros"}
    assert cuerpo["tiene_comprobante"] is False
    assert guardada["taller_id"] == repos.taller["_id"]
    assert guardada["registrado_por"] == repos.taller["usuario_id"]
    assert guardada["codigo_id"] == repos.codigos.codigos[0]["_id"]
    assert guardada["vehiculo_id"] == repos.vehiculo["_id"]
    assert guardada["fecha_registro"].tzinfo is not None
    assert guardada["fecha_registro"].microsecond % 1000 == 0, "misma precisión que MongoDB"
    assert guardada["hash_anterior"] is None
    assert verificar_cadena(repos.intervenciones.intervenciones)


def test_al_registrar_el_codigo_queda_utilizado_por_el_taller(cliente, repos):
    _registrar(cliente, repos)

    codigo = repos.codigos.codigos[0]
    assert codigo["estado"] == "utilizado"
    assert codigo["taller_id"] == repos.taller["_id"]
    assert codigo["fecha_uso"] is not None


def test_el_mismo_codigo_no_sirve_para_una_segunda_intervencion(cliente, repos):
    _registrar(cliente, repos)

    respuesta = _registrar(cliente, repos)

    assert respuesta.status_code == 403
    assert respuesta.json()["detail"] == CODIGO_INVALIDO
    assert len(repos.intervenciones.intervenciones) == 1


def test_con_codigo_invalido_no_se_registra(cliente, repos):
    respuesta = _registrar(cliente, repos, codigo=_incorrecto(repos.codigo))

    assert respuesta.status_code == 403
    assert repos.intervenciones.intervenciones == []
    assert repos.codigos.codigos[0]["intentos_fallidos"] == 1


def test_campos_incompletos_indica_cuales(cliente, repos):
    respuesta = _registrar(cliente, repos, fecha_intervencion="", kilometraje=None, tipo="", items=[])

    assert respuesta.status_code == 422
    assert respuesta.json()["campos"] == {
        "fecha_intervencion": "Completá este campo.",
        "kilometraje": "Completá este campo.",
        "tipo": "Completá este campo.",
        "items": "Agregá al menos un ítem.",
    }
    assert repos.codigos.codigos[0]["estado"] == "vigente", "un formulario incompleto no consume el código"


def test_errores_de_cada_item(cliente, repos):
    respuesta = _registrar(cliente, repos, items=[{"descripcion": "Aceite", "cantidad": 4}, {"descripcion": "", "cantidad": 0}])

    assert respuesta.json()["campos"] == {
        "items.1.descripcion": "Completá este campo.",
        "items.1.cantidad": "Ingresá una cantidad entre 1 y 9.999.",
    }


@pytest.mark.parametrize(
    ("cambios", "campos"),
    [
        ({"fecha_intervencion": (hoy_en_argentina() + timedelta(days=1)).isoformat()},
         {"fecha_intervencion": "La fecha no puede ser posterior a hoy."}),
        ({"tipo": "Pintura"}, {"tipo": "Elegí un tipo de intervención de la lista."}),
        ({"kilometraje": -1}, {"kilometraje": "Ingresá un kilometraje entre 0 y 2.000.000 km."}),
        ({"proxima_revision": {"detalle": "Revisar frenos"}},
         {"proxima_revision": "Indicá el kilometraje o la fecha de la próxima revisión."}),
        ({"proxima_revision": {"kilometraje": 90000}},
         {"proxima_revision": "El kilometraje de la próxima revisión tiene que ser mayor al del servicio."}),
    ],
)
def test_validaciones_de_los_datos_del_servicio(cliente, repos, cambios, campos):
    respuesta = _registrar(cliente, repos, **cambios)

    assert respuesta.status_code == 422
    assert respuesta.json()["campos"] == campos


def test_sin_proxima_revision_ni_descripcion(cliente, repos):
    respuesta = _registrar(cliente, repos, proxima_revision=None, descripcion="  ")

    assert respuesta.status_code == 201
    assert respuesta.json()["proxima_revision"] is None
    assert respuesta.json()["descripcion"] is None


def test_datos_sin_formato_json(cliente, repos):
    respuesta = cliente.post("/api/taller/intervenciones", data={"datos": "no es json"}, headers=repos.headers)

    assert respuesta.status_code == 422
    assert respuesta.json()["campos"] == {"general": "Los datos enviados no tienen un formato válido."}


# --- Comprobante ---


def test_comprobante_pdf_se_guarda_y_lo_descargan_el_taller_y_el_propietario(cliente, repos):
    respuesta = _registrar(cliente, repos, archivo=("factura.pdf", PDF, "application/pdf"))

    assert respuesta.status_code == 201
    assert respuesta.json()["tiene_comprobante"] is True
    [(contenido, nombre, tipo)] = repos.comprobantes.archivos.values()
    assert (contenido, nombre, tipo) == (PDF, "factura.pdf", "application/pdf")

    ruta = f"/api/intervenciones/{respuesta.json()['id']}/comprobante"
    for headers in (repos.headers, _token(repos.propietario_id, Rol.PROPIETARIO)):
        descarga = cliente.get(ruta, headers=headers)
        assert descarga.status_code == 200
        assert descarga.content == PDF
        assert descarga.headers["content-type"] == "application/pdf"


def test_el_comprobante_no_lo_ven_otros_talleres_ni_otros_propietarios(cliente, repos):
    intervencion_id = _registrar(cliente, repos, archivo=("factura.pdf", PDF, "application/pdf")).json()["id"]
    _, otro_taller = _taller(repos.talleres, "Taller Güemes")

    for headers in (otro_taller, _token(ObjectId(), Rol.PROPIETARIO)):
        respuesta = cliente.get(f"/api/intervenciones/{intervencion_id}/comprobante", headers=headers)
        assert respuesta.status_code == 404
    assert cliente.get(f"/api/intervenciones/{intervencion_id}/comprobante").status_code == 401


@pytest.mark.parametrize(
    ("archivo", "mensaje"),
    [
        (("factura.pdf", b"no soy un pdf", "application/pdf"), "El comprobante tiene que ser un archivo PDF, JPG o PNG."),
        (("foto.png", b"GIF89a....", "image/png"), "El comprobante tiene que ser un archivo PDF, JPG o PNG."),
        (("grande.pdf", b"%PDF-" + b"0" * (5 * 1024 * 1024), "application/pdf"), "El comprobante no puede superar los 5 MB."),
    ],
)
def test_comprobante_invalido_no_registra_ni_consume_el_codigo(cliente, repos, archivo, mensaje):
    respuesta = _registrar(cliente, repos, archivo=archivo)

    assert respuesta.status_code == 422
    assert respuesta.json()["campos"] == {"comprobante": mensaje}
    assert repos.intervenciones.intervenciones == []
    assert repos.codigos.codigos[0]["estado"] == "vigente"


@pytest.mark.parametrize(("nombre", "contenido"), [("foto.jpg", b"\xff\xd8\xff\xe0JFIF"), ("foto.png", b"\x89PNG\r\n\x1a\n...")])
def test_acepta_jpg_y_png_por_su_contenido(cliente, repos, nombre, contenido):
    respuesta = _registrar(cliente, repos, archivo=(nombre, contenido, "application/octet-stream"))

    assert respuesta.status_code == 201


def test_si_el_registro_falla_se_borra_el_comprobante_y_el_codigo_sigue_vigente(cliente, repos, monkeypatch):
    async def falla(intervencion, sesion=None):
        raise RuntimeError("se cayó la base")

    monkeypatch.setattr(repos.intervenciones, "insertar", falla)

    with pytest.raises(RuntimeError):
        _registrar(cliente, repos, archivo=("factura.pdf", PDF, "application/pdf"))
    assert repos.comprobantes.archivos == {}
    assert repos.codigos.codigos[0]["estado"] == "vigente"


# --- Registros realizados ---


def test_registros_realizados_muestra_solo_los_del_taller_del_mas_reciente_al_mas_antiguo(cliente, repos):
    _registrar(cliente, repos, kilometraje=100210)
    otro_taller, headers_otro = _taller(repos.talleres, "Taller Güemes")
    repos.codigo = _generar_codigo(repos)
    _registrar(cliente, repos, headers=headers_otro, kilometraje=101000)
    repos.codigo = _generar_codigo(repos)
    _registrar(cliente, repos, kilometraje=102500, tipo="Cambio de aceite y filtros")

    respuesta = cliente.get("/api/taller/intervenciones", headers=repos.headers)

    assert respuesta.status_code == 200
    assert [(r["kilometraje"], r["tipo"], r["dominio"]) for r in respuesta.json()] == [
        (102500, "Cambio de aceite y filtros", "AE123CD"),
        (100210, "Frenos", "AE123CD"),
    ]
    assert verificar_cadena(repos.intervenciones.intervenciones), "los tres registros encadenan en el vehículo"


# --- Acceso ---


@pytest.mark.parametrize("estado", ["pendiente", "rechazado"])
def test_un_taller_no_aprobado_no_puede_operar(cliente, repos, estado):
    _, headers = _taller(repos.talleres, "Taller Nuevo", estado=estado)

    assert _autorizar(cliente, repos, headers=headers).status_code == 403
    assert _registrar(cliente, repos, headers=headers).status_code == 403
    assert cliente.get("/api/taller/intervenciones", headers=headers).status_code == 403


@pytest.mark.parametrize("rol", [Rol.PROPIETARIO, Rol.ADMINISTRADOR])
def test_otros_roles_no_usan_los_endpoints_del_taller(cliente, repos, rol):
    headers = _token(ObjectId(), rol)

    assert _autorizar(cliente, repos, headers=headers).status_code == 403
    assert _registrar(cliente, repos, headers=headers).status_code == 403
    assert cliente.post("/api/taller/autorizacion", json={}).status_code == 401
