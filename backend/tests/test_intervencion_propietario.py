"""HU-008: intervención autorreportada por el propietario. Usa repositorios y transacción en memoria."""

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
    obtener_repositorio_intervenciones,
    obtener_repositorio_talleres,
    obtener_repositorio_vehiculos,
    obtener_transaccion,
)
from app.servicios.hash import verificar_cadena
from tests.falsos import (
    AlmacenComprobantesFalso,
    RepositorioIntervencionesFalso,
    RepositorioTalleresFalso,
    RepositorioVehiculosFalso,
    TransaccionFalsa,
)

PDF = b"%PDF-1.7\n% factura de la bateria\n"


def _token(usuario_id, rol):
    return {"Authorization": f"Bearer {crear_token(str(usuario_id), rol)}"}


@pytest.fixture
def repos(cliente):
    r = SimpleNamespace(
        vehiculos=RepositorioVehiculosFalso(),
        intervenciones=RepositorioIntervencionesFalso(),
        comprobantes=AlmacenComprobantesFalso(),
        talleres=RepositorioTalleresFalso(),
    )
    transaccion = TransaccionFalsa(r.intervenciones)
    app.dependency_overrides[obtener_repositorio_vehiculos] = lambda: r.vehiculos
    app.dependency_overrides[obtener_repositorio_intervenciones] = lambda: r.intervenciones
    app.dependency_overrides[obtener_almacen_comprobantes] = lambda: r.comprobantes
    app.dependency_overrides[obtener_repositorio_talleres] = lambda: r.talleres
    app.dependency_overrides[obtener_transaccion] = lambda: transaccion
    r.propietario_id = ObjectId()
    r.headers = _token(r.propietario_id, Rol.PROPIETARIO)
    r.vehiculo = {
        "_id": ObjectId(), "dominio": "AE123CD", "marca": "Volkswagen", "modelo": "Gol Trend", "anio": 2020,
        "propietario_id": r.propietario_id, "fecha_vinculacion": datetime.now(UTC),
    }
    r.vehiculos.vehiculos.append(r.vehiculo)
    return r


def _datos(**cambios):
    return {
        "fecha_intervencion": (hoy_en_argentina() - timedelta(days=3)).isoformat(),
        "kilometraje": 99870,
        "tipo": "Batería y sistema eléctrico",
        "descripcion": "Reemplazo de la batería original por falla en el arranque en frío.",
        "items": [{"descripcion": "Batería 12 V 65 Ah", "cantidad": 1}],
        "proxima_revision": {"fecha": (hoy_en_argentina() + timedelta(days=700)).isoformat()},
        **cambios,
    }


def _registrar(cliente, repos, headers=None, archivo=None, vehiculo_id=None, **cambios):
    return cliente.post(
        f"/api/vehiculos/{vehiculo_id or repos.vehiculo['_id']}/intervenciones",
        data={"datos": json.dumps(_datos(**cambios))},
        files={"comprobante": archivo} if archivo else None,
        headers=headers or repos.headers,
    )


def test_se_registra_como_autorreportada_por_el_propietario(cliente, repos):
    respuesta = _registrar(cliente, repos)

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["origen"] == "propietario"
    assert cuerpo["dominio"] == "AE123CD"
    assert cuerpo["proxima_revision"]["kilometraje"] is None
    guardada = repos.intervenciones.intervenciones[0]
    assert guardada["taller_id"] is None
    assert guardada["codigo_id"] is None, "no necesita código de autorización"
    assert guardada["registrado_por"] == repos.propietario_id
    assert verificar_cadena(repos.intervenciones.intervenciones)


def test_campos_incompletos_indica_cuales(cliente, repos):
    respuesta = _registrar(cliente, repos, kilometraje=None, tipo="", items=[{"descripcion": " ", "cantidad": 1}])

    assert respuesta.status_code == 422
    assert respuesta.json()["campos"] == {
        "kilometraje": "Completá este campo.",
        "tipo": "Completá este campo.",
        "items.0.descripcion": "Completá este campo.",
    }
    assert repos.intervenciones.intervenciones == []


def test_encadena_con_los_registros_anteriores_del_vehiculo(cliente, repos):
    _registrar(cliente, repos, kilometraje=98450)
    _registrar(cliente, repos, kilometraje=99870)

    primera, segunda = repos.intervenciones.intervenciones
    assert segunda["hash_anterior"] == primera["hash"]
    assert verificar_cadena(repos.intervenciones.intervenciones)


def test_mis_vehiculos_informa_el_ultimo_kilometraje_y_servicio(cliente, repos):
    hace_10_dias = hoy_en_argentina() - timedelta(days=10)
    _registrar(cliente, repos, kilometraje=99870)
    _registrar(cliente, repos, kilometraje=98450, fecha_intervencion=hace_10_dias.isoformat())

    [vehiculo] = cliente.get("/api/vehiculos", headers=repos.headers).json()

    # Cuenta la fecha del servicio, no el orden de carga: la segunda carga es un servicio anterior.
    assert vehiculo["ultima_lectura"]["kilometraje"] == 99870
    hace_3_dias = hoy_en_argentina() - timedelta(days=3)
    assert datetime.fromisoformat(vehiculo["ultima_lectura"]["fecha"]) == inicio_del_dia(hace_3_dias)


def test_con_comprobante_lo_descarga_el_propietario_y_no_un_taller(cliente, repos):
    respuesta = _registrar(cliente, repos, archivo=("factura-bateria.pdf", PDF, "application/pdf"))
    ruta = f"/api/intervenciones/{respuesta.json()['id']}/comprobante"
    usuario_taller = ObjectId()
    repos.talleres.talleres.append({"_id": ObjectId(), "usuario_id": usuario_taller, "estado_solicitud": "aprobado"})

    assert respuesta.json()["tiene_comprobante"] is True
    assert cliente.get(ruta, headers=repos.headers).content == PDF
    assert cliente.get(ruta, headers=_token(usuario_taller, Rol.TALLER)).status_code == 404


def test_comprobante_invalido(cliente, repos):
    respuesta = _registrar(cliente, repos, archivo=("factura.pdf", b"texto", "application/pdf"))

    assert respuesta.status_code == 422
    assert respuesta.json()["campos"] == {"comprobante": "El comprobante tiene que ser un archivo PDF, JPG o PNG."}
    assert repos.intervenciones.intervenciones == []


def test_no_se_puede_registrar_en_un_vehiculo_ajeno(cliente, repos):
    otro = _token(ObjectId(), Rol.PROPIETARIO)

    respuesta = _registrar(cliente, repos, headers=otro)

    assert respuesta.status_code == 404
    assert respuesta.json()["detail"] == "El vehículo no está vinculado a tu cuenta."
    assert _registrar(cliente, repos, vehiculo_id="no-es-un-id").status_code == 404
    assert repos.intervenciones.intervenciones == []


@pytest.mark.parametrize("rol", [Rol.TALLER, Rol.ADMINISTRADOR])
def test_otros_roles_no_registran_autorreportadas(cliente, repos, rol):
    assert _registrar(cliente, repos, headers=_token(ObjectId(), rol)).status_code == 403
