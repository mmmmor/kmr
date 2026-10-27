"""Cadena de hash por vehículo e inmutabilidad de las intervenciones."""

import asyncio
import inspect
from datetime import UTC, date, datetime

import pytest
from bson import ObjectId

from app.esquemas.intervenciones import IntervencionEntrada
from app.main import app
from app.modelos.intervencion import Origen
from app.repositorios import intervenciones as modulo_repositorio
from app.repositorios.intervenciones import CadenaModificada, RepositorioIntervenciones
from app.servicios import intervenciones as servicio
from app.servicios.hash import calcular_hash, json_canonico, verificar_cadena
from tests.falsos import RepositorioIntervencionesFalso, TransaccionFalsa

DATOS = IntervencionEntrada(
    fecha_intervencion=date(2026, 8, 14),
    kilometraje=98450,
    tipo="Cambio de aceite y filtros",
    items=[{"descripcion": "Aceite 5W-40 (litros)", "cantidad": 4}],
)


def _registrar(repo, vehiculo_id, kilometraje=98450):
    intervencion = servicio.nueva(
        DATOS.model_copy(update={"kilometraje": kilometraje}), vehiculo_id, Origen.PROPIETARIO, ObjectId()
    )
    return asyncio.run(servicio.insertar_encadenada(intervencion, repo, TransaccionFalsa(repo)))


def _cadena(repo, vehiculo_id):
    return asyncio.run(repo.listar_por_vehiculo(vehiculo_id))


# --- JSON canónico ---


def test_json_canonico_ordena_claves_sin_espacios_y_excluye_id_y_hash():
    texto = json_canonico({
        "_id": ObjectId(),
        "hash": "abc",
        "tipo": "Frenos",
        "items": [{"descripcion": "Disco", "cantidad": 2}],
        "vehiculo_id": ObjectId("6ae0d653d45ceb47b2b2da2a"),
        "fecha_registro": datetime(2026, 9, 26, 12, 41, 5, 123456, tzinfo=UTC),
        "descripcion": None,
    })

    assert texto == (
        '{"descripcion":null,"fecha_registro":"2026-09-26T12:41:05.123Z",'
        '"items":[{"cantidad":2,"descripcion":"Disco"}],"tipo":"Frenos",'
        '"vehiculo_id":"6ae0d653d45ceb47b2b2da2a"}'
    )


def test_el_hash_depende_de_cada_campo_y_del_anterior():
    registro = {"kilometraje": 98450, "tipo": "Frenos", "hash_anterior": None}

    base = calcular_hash(registro, None)

    assert base == calcular_hash(dict(registro), None)
    assert base != calcular_hash({**registro, "kilometraje": 98451}, None)
    assert base != calcular_hash(registro, "otro-anterior")
    assert len(base) == 64


# --- Encadenamiento ---


def test_cada_registro_encadena_con_el_anterior_del_mismo_vehiculo():
    repo = RepositorioIntervencionesFalso()
    auto, otro_auto = ObjectId(), ObjectId()

    primero = _registrar(repo, auto, 98450)
    del_otro = _registrar(repo, otro_auto, 50000)
    segundo = _registrar(repo, auto, 100210)

    assert primero["hash_anterior"] is None
    assert del_otro["hash_anterior"] is None, "la cadena es por vehículo"
    assert segundo["hash_anterior"] == primero["hash"]
    assert segundo["hash"] == calcular_hash(segundo, primero["hash"])
    assert verificar_cadena(_cadena(repo, auto))
    assert verificar_cadena(_cadena(repo, otro_auto))


def test_una_carga_simultanea_hace_recalcular_el_encadenamiento(monkeypatch):
    repo, auto = RepositorioIntervencionesFalso(), ObjectId()
    primero = _registrar(repo, auto, 98450)
    simultanea = _registrar(repo, auto, 99000)
    ultima_registrada = repo.ultima_registrada
    lecturas = []

    async def lectura_desactualizada(vehiculo_id, sesion=None):
        # La primera lectura todavía no ve la carga simultánea, que se confirmó justo antes.
        lecturas.append(vehiculo_id)
        return primero if len(lecturas) == 1 else await ultima_registrada(vehiculo_id, sesion)

    monkeypatch.setattr(repo, "ultima_registrada", lectura_desactualizada)
    segundo = _registrar(repo, auto, 100210)

    assert len(lecturas) == 2, "el índice único rechazó el primer intento y se reintentó"
    assert segundo["hash_anterior"] == simultanea["hash"]
    assert verificar_cadena(_cadena(repo, auto))


def test_si_la_cadena_no_deja_de_cambiar_se_rinde(monkeypatch):
    repo, auto = RepositorioIntervencionesFalso(), ObjectId()
    _registrar(repo, auto)

    async def siempre_desactualizada(vehiculo_id, sesion=None):
        return None  # siempre cree que es el primero: choca con el registro existente

    monkeypatch.setattr(repo, "ultima_registrada", siempre_desactualizada)

    with pytest.raises(CadenaModificada):
        _registrar(repo, auto)
    assert len(repo.intervenciones) == 1


# --- Verificación ---


def test_detecta_un_registro_modificado():
    repo, auto = RepositorioIntervencionesFalso(), ObjectId()
    for km in (90000, 95000, 100000):
        _registrar(repo, auto, km)

    repo.intervenciones[1]["kilometraje"] = 59000

    assert not verificar_cadena(_cadena(repo, auto))


def test_detecta_un_registro_modificado_aunque_recalculen_su_hash():
    repo, auto = RepositorioIntervencionesFalso(), ObjectId()
    for km in (90000, 95000, 100000):
        _registrar(repo, auto, km)
    alterado = repo.intervenciones[1]

    alterado["kilometraje"] = 59000
    alterado["hash"] = calcular_hash(alterado, alterado["hash_anterior"])

    assert not verificar_cadena(_cadena(repo, auto)), "el siguiente registro apunta al hash original"


def test_detecta_un_registro_intermedio_eliminado():
    repo, auto = RepositorioIntervencionesFalso(), ObjectId()
    for km in (90000, 95000, 100000):
        _registrar(repo, auto, km)

    del repo.intervenciones[1]

    assert not verificar_cadena(_cadena(repo, auto))


def test_una_cadena_vacia_es_valida():
    assert verificar_cadena([])


# --- Inmutabilidad ---


def test_el_repositorio_de_intervenciones_solo_inserta_y_consulta():
    publicos = {nombre for nombre, _ in inspect.getmembers(RepositorioIntervenciones) if not nombre.startswith("_")}

    assert publicos == {
        "insertar", "buscar", "ultima_registrada", "ultima_lectura", "listar_por_vehiculo", "listar_por_taller",
    }
    codigo = inspect.getsource(modulo_repositorio)
    for operacion in ("update_one", "update_many", "replace_one", "delete_one", "delete_many", "find_one_and_"):
        assert operacion not in codigo


def test_la_api_no_tiene_rutas_para_editar_o_borrar():
    metodos = {metodo for ruta in app.routes for metodo in getattr(ruta, "methods", set())}

    assert metodos.isdisjoint({"PUT", "PATCH", "DELETE"})
