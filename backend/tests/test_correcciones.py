"""HU-011: correcciones vinculadas. Usa repositorios y transacción en memoria."""

import asyncio
import copy
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from bson import ObjectId

from app.core.fechas import hoy_en_argentina
from app.core.seguridad import crear_token
from app.esquemas.intervenciones import IntervencionEntrada
from app.main import app
from app.modelos.intervencion import Origen
from app.modelos.usuario import Rol
from app.routers.dependencias import (
    obtener_repositorio_intervenciones,
    obtener_repositorio_talleres,
    obtener_repositorio_vehiculos,
    obtener_transaccion,
)
from app.servicios import intervenciones as servicio
from app.servicios.hash import verificar_cadena
from tests.falsos import (
    RepositorioIntervencionesFalso,
    RepositorioTalleresFalso,
    RepositorioVehiculosFalso,
    TransaccionFalsa,
)


def _token(usuario_id, rol):
    return {"Authorization": f"Bearer {crear_token(str(usuario_id), rol)}"}


def _taller(repos, razon_social):
    taller = {
        "_id": ObjectId(), "usuario_id": ObjectId(), "razon_social": razon_social, "estado_solicitud": "aprobado",
    }
    repos.talleres.talleres.append(taller)
    return taller, _token(taller["usuario_id"], Rol.TALLER)


@pytest.fixture
def repos(cliente):
    r = SimpleNamespace(
        vehiculos=RepositorioVehiculosFalso(),
        intervenciones=RepositorioIntervencionesFalso(),
        talleres=RepositorioTalleresFalso(),
    )
    r.intervenciones.vehiculos = r.vehiculos
    transaccion = TransaccionFalsa(r.intervenciones)
    app.dependency_overrides[obtener_repositorio_vehiculos] = lambda: r.vehiculos
    app.dependency_overrides[obtener_repositorio_intervenciones] = lambda: r.intervenciones
    app.dependency_overrides[obtener_repositorio_talleres] = lambda: r.talleres
    app.dependency_overrides[obtener_transaccion] = lambda: transaccion
    r.propietario_id = ObjectId()
    r.propietario = _token(r.propietario_id, Rol.PROPIETARIO)
    r.vehiculo = {
        "_id": ObjectId(), "dominio": "AE123CD", "marca": "Volkswagen", "modelo": "Gol Trend", "anio": 2020,
        "propietario_id": r.propietario_id, "fecha_vinculacion": datetime.now(UTC),
    }
    r.vehiculos.vehiculos.append(r.vehiculo)
    r.taller, r.headers_taller = _taller(r, "Lubricentro San Martín")
    return r


def _fecha(dias_atras):
    return hoy_en_argentina() - timedelta(days=dias_atras)


def _cargar(repos, km, dias_atras, taller=None):
    datos = IntervencionEntrada(
        fecha_intervencion=_fecha(dias_atras),
        kilometraje=km,
        tipo="Frenos",
        descripcion="Cambio de pastillas delanteras.",
        items=[{"descripcion": "Juego de pastillas de freno delanteras", "cantidad": 1}],
    )
    intervencion = servicio.nueva(
        datos,
        repos.vehiculo["_id"],
        Origen.TALLER if taller else Origen.PROPIETARIO,
        taller["usuario_id"] if taller else repos.propietario_id,
        taller_id=taller["_id"] if taller else None,
    )
    return asyncio.run(
        servicio.insertar_encadenada(intervencion, repos.intervenciones, TransaccionFalsa(repos.intervenciones))
    )


def _corregir(cliente, registro, headers, motivo="Error de tipeo en el kilometraje.", **cambios):
    """Envía los datos completos del registro con los cambios, como el panel de corrección."""
    datos = {
        "fecha_intervencion": registro["fecha_intervencion"].astimezone(UTC).date().isoformat(),
        "kilometraje": registro["kilometraje"],
        "tipo": registro["tipo"],
        "descripcion": registro["descripcion"],
        "items": registro["items"],
        "proxima_revision": registro["proxima_revision"],
        "motivo": motivo,
        **cambios,
    }
    return cliente.post(f"/api/intervenciones/{registro['_id']}/correcciones", json=datos, headers=headers)


def test_la_correccion_es_un_registro_nuevo_vinculado_y_el_original_no_cambia(cliente, repos):
    _cargar(repos, 84100, 200, taller=repos.taller)
    original = _cargar(repos, 48100, 70, taller=repos.taller)
    antes = copy.deepcopy(repos.intervenciones.intervenciones)

    respuesta = _corregir(cliente, original, repos.headers_taller, kilometraje=91800)

    assert respuesta.status_code == 201
    assert respuesta.json()["kilometraje"] == 91800
    assert repos.intervenciones.intervenciones[:2] == antes, "los registros anteriores quedan intactos"
    correccion = repos.intervenciones.intervenciones[2]
    assert correccion["corrige_a"] == original["_id"]
    assert correccion["motivo_correccion"] == "Error de tipeo en el kilometraje."
    assert (correccion["origen"], correccion["taller_id"]) == ("taller", repos.taller["_id"])
    assert correccion["registrado_por"] == repos.taller["usuario_id"]
    assert correccion["codigo_id"] is None, "corregir no necesita un código nuevo"
    assert correccion["tipo"] == original["tipo"] and correccion["items"] == original["items"]
    assert verificar_cadena(repos.intervenciones.intervenciones)


def test_la_correccion_se_valida_contra_lo_anterior_al_registro_que_corrige(cliente, repos):
    _cargar(repos, 84100, 200, taller=repos.taller)
    original = _cargar(repos, 48100, 70, taller=repos.taller)
    assert original["alerta_kilometraje"] == "kilometraje_inferior"

    respuesta = _corregir(cliente, original, repos.headers_taller, kilometraje=91800)

    assert respuesta.json()["alerta_kilometraje"] is None
    vehiculo = cliente.get("/api/vehiculos", headers=repos.propietario).json()[0]
    assert vehiculo["ultima_lectura"]["kilometraje"] == 91800, "cuenta el valor corregido"


def test_el_historial_muestra_los_dos_registros_vinculados(cliente, repos):
    original = _cargar(repos, 48100, 70, taller=repos.taller)
    _corregir(cliente, original, repos.headers_taller, kilometraje=91800)

    correccion, corregido = cliente.get(
        f"/api/vehiculos/{repos.vehiculo['_id']}/historial", headers=repos.propietario
    ).json()["intervenciones"]

    assert correccion["corrige_a"]["id"] == str(original["_id"])
    assert correccion["campos_corregidos"] == ["kilometraje"]
    assert corregido["corregido_por"]["id"] == correccion["id"]


def test_registros_realizados_del_taller_muestra_las_correcciones(cliente, repos):
    original = _cargar(repos, 48100, 70, taller=repos.taller)
    _corregir(cliente, original, repos.headers_taller, kilometraje=91800)

    correccion, corregido = cliente.get("/api/taller/intervenciones", headers=repos.headers_taller).json()

    assert correccion["corrige_a"]["id"] == corregido["id"]
    assert corregido["corregido_por"]["id"] == correccion["id"]


def test_un_taller_no_puede_corregir_registros_de_otro_taller(cliente, repos):
    original = _cargar(repos, 48100, 70, taller=repos.taller)
    _, headers_otro = _taller(repos, "Taller Güemes")

    respuesta = _corregir(cliente, original, headers_otro, kilometraje=91800)

    assert respuesta.status_code == 403
    assert respuesta.json()["detail"] == "Solo podés corregir los registros que cargó tu taller."
    assert len(repos.intervenciones.intervenciones) == 1


def test_un_taller_no_corrige_intervenciones_autorreportadas(cliente, repos):
    autorreportada = _cargar(repos, 48100, 70)

    respuesta = _corregir(cliente, autorreportada, repos.headers_taller, kilometraje=91800)

    assert respuesta.status_code == 403


def test_el_propietario_corrige_sus_autorreportadas(cliente, repos):
    autorreportada = _cargar(repos, 48100, 70)

    respuesta = _corregir(cliente, autorreportada, repos.propietario, tipo="Cambio de aceite y filtros")

    assert respuesta.status_code == 201
    correccion = repos.intervenciones.intervenciones[-1]
    assert (correccion["origen"], correccion["taller_id"]) == ("propietario", None)
    assert correccion["registrado_por"] == repos.propietario_id


def test_el_propietario_no_corrige_registros_de_un_taller(cliente, repos):
    del_taller = _cargar(repos, 48100, 70, taller=repos.taller)

    respuesta = _corregir(cliente, del_taller, repos.propietario, kilometraje=91800)

    assert respuesta.status_code == 403
    assert "Un registro de un taller lo corrige ese taller." in respuesta.json()["detail"]


def test_un_propietario_no_ve_registros_de_vehiculos_ajenos(cliente, repos):
    autorreportada = _cargar(repos, 48100, 70)

    respuesta = _corregir(cliente, autorreportada, _token(ObjectId(), Rol.PROPIETARIO), kilometraje=91800)

    assert respuesta.status_code == 404


def test_el_motivo_es_obligatorio(cliente, repos):
    original = _cargar(repos, 48100, 70, taller=repos.taller)

    respuesta = _corregir(cliente, original, repos.headers_taller, motivo="  ", kilometraje=91800)

    assert respuesta.status_code == 422
    assert respuesta.json()["campos"] == {"motivo": "Completá este campo."}
    assert len(repos.intervenciones.intervenciones) == 1


def test_el_valor_corregido_se_valida_como_en_el_registro(cliente, repos):
    original = _cargar(repos, 48100, 70, taller=repos.taller)

    respuesta = _corregir(cliente, original, repos.headers_taller, fecha_intervencion=_fecha(-1).isoformat())

    assert respuesta.status_code == 422
    assert respuesta.json()["campos"] == {"fecha_intervencion": "La fecha no puede ser posterior a hoy."}


def test_sin_cambios_no_hay_nada_que_corregir(cliente, repos):
    original = _cargar(repos, 48100, 70, taller=repos.taller)

    respuesta = _corregir(cliente, original, repos.headers_taller)

    assert respuesta.status_code == 422
    assert len(repos.intervenciones.intervenciones) == 1


def test_un_registro_corregido_no_se_vuelve_a_corregir_pero_su_correccion_si(cliente, repos):
    original = _cargar(repos, 48100, 70, taller=repos.taller)
    _corregir(cliente, original, repos.headers_taller, kilometraje=91800)
    correccion = repos.intervenciones.intervenciones[-1]

    otra = _corregir(cliente, original, repos.headers_taller, kilometraje=91900)
    de_la_correccion = _corregir(cliente, correccion, repos.headers_taller, kilometraje=91900)

    assert otra.status_code == 409
    assert de_la_correccion.status_code == 201
    assert repos.intervenciones.intervenciones[-1]["corrige_a"] == correccion["_id"]
    assert verificar_cadena(repos.intervenciones.intervenciones)


@pytest.mark.parametrize("intervencion_id", [str(ObjectId()), "no-es-un-id"])
def test_registro_inexistente(cliente, repos, intervencion_id):
    respuesta = cliente.post(
        f"/api/intervenciones/{intervencion_id}/correcciones",
        json={
            "fecha_intervencion": _fecha(1).isoformat(), "kilometraje": 1, "tipo": "Frenos",
            "items": [{"descripcion": "Pastillas", "cantidad": 1}], "motivo": "Error.",
        },
        headers=repos.headers_taller,
    )

    assert respuesta.status_code == 404


def test_el_administrador_no_corrige(cliente, repos):
    original = _cargar(repos, 48100, 70, taller=repos.taller)

    respuesta = _corregir(cliente, original, _token(ObjectId(), Rol.ADMINISTRADOR), kilometraje=91800)

    assert respuesta.status_code == 403
