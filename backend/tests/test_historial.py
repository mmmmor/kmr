"""HU-012: historial del propietario. Usa repositorios y transacción en memoria."""

import asyncio
from datetime import datetime, timedelta

from bson import ObjectId

from app.core.fechas import hoy_en_argentina, inicio_del_dia
from app.esquemas.intervenciones import IntervencionEntrada
from app.modelos.intervencion import Origen
from app.modelos.usuario import Rol
from app.servicios import intervenciones as servicio
from tests.falsos import TransaccionFalsa
from tests.test_intervencion_propietario import _token, repos  # noqa: F401 (fixture)


def _cargar(repos, km, dias_atras, tipo="Cambio de aceite y filtros", taller=None, corrige=None, motivo=None):
    """Inserta un registro como lo haría el servicio. Las correcciones (HU-011) se arman a mano."""
    datos = IntervencionEntrada(
        fecha_intervencion=hoy_en_argentina() - timedelta(days=dias_atras),
        kilometraje=km,
        tipo=tipo,
        items=[{"descripcion": "Filtro de aceite", "cantidad": 1}],
    )
    intervencion = servicio.nueva(
        datos,
        repos.vehiculo["_id"],
        Origen.TALLER if taller else Origen.PROPIETARIO,
        ObjectId(),
        taller_id=taller["_id"] if taller else None,
    )
    if corrige is not None:
        intervencion.update(corrige_a=corrige["_id"], motivo_correccion=motivo)
    return asyncio.run(
        servicio.insertar_encadenada(intervencion, repos.intervenciones, TransaccionFalsa(repos.intervenciones))
    )


def _taller(repos, razon_social="Lubricentro San Martín"):
    taller = {"_id": ObjectId(), "usuario_id": ObjectId(), "razon_social": razon_social, "estado_solicitud": "aprobado"}
    repos.talleres.talleres.append(taller)
    return taller


def _historial(cliente, repos, headers=None, vehiculo_id=None):
    return cliente.get(
        f"/api/vehiculos/{vehiculo_id or repos.vehiculo['_id']}/historial", headers=headers or repos.headers
    )


def test_sin_intervenciones_devuelve_el_vehiculo_y_una_lista_vacia(cliente, repos):
    respuesta = _historial(cliente, repos)

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["vehiculo"]["dominio"] == "AE123CD"
    assert cuerpo["intervenciones"] == []
    assert cuerpo["integridad_verificada"] is True


def test_ordena_del_servicio_mas_reciente_al_mas_antiguo_no_por_orden_de_carga(cliente, repos):
    _cargar(repos, 84100, 200)
    _cargar(repos, 98450, 70)
    _cargar(repos, 72300, 400, tipo="Frenos")  # servicio viejo cargado al final

    intervenciones = _historial(cliente, repos).json()["intervenciones"]

    assert [i["kilometraje"] for i in intervenciones] == [98450, 84100, 72300]
    assert intervenciones[0]["fecha"] == intervenciones[0]["fecha_intervencion"]


def test_identifica_al_taller_verificado_o_el_autorreporte(cliente, repos):
    taller = _taller(repos)
    _cargar(repos, 84100, 200)
    _cargar(repos, 98450, 70, taller=taller)

    del_taller, autorreportada = _historial(cliente, repos).json()["intervenciones"]

    assert (del_taller["origen"], del_taller["taller"]) == ("taller", "Lubricentro San Martín")
    assert (autorreportada["origen"], autorreportada["taller"]) == ("propietario", None)


def test_la_correccion_va_arriba_del_registro_que_corrige_y_se_vinculan(cliente, repos):
    taller = _taller(repos)
    _cargar(repos, 84100, 200, taller=taller)
    con_error = _cargar(repos, 48100, 70, taller=taller)
    correccion = _cargar(repos, 91800, 70, taller=taller, corrige=con_error, motivo="Error de tipeo.")
    _cargar(repos, 98450, 10, taller=taller)

    cuerpo = _historial(cliente, repos).json()
    reciente, corrige, corregido, primero = cuerpo["intervenciones"]

    assert [i["kilometraje"] for i in cuerpo["intervenciones"]] == [98450, 91800, 48100, 84100]
    assert corrige["corrige_a"]["id"] == str(con_error["_id"])
    assert datetime.fromisoformat(corrige["corrige_a"]["fecha"]) == con_error["fecha_intervencion"]
    assert corrige["motivo_correccion"] == "Error de tipeo."
    assert corrige["campos_corregidos"] == ["kilometraje"]
    # La corrección se muestra con el día en que se cargó, y así la nombra el original.
    assert datetime.fromisoformat(corrige["fecha"]) == correccion["fecha_registro"]
    assert corregido["corregido_por"] == {"id": str(correccion["_id"]), "fecha": corrige["fecha"]}
    assert corregido["alerta_kilometraje"]["tipo"] == "kilometraje_inferior", "el original conserva su alerta"
    assert corrige["alerta_kilometraje"] is None, "la corrección se valida contra lo anterior al original"
    assert reciente["corrige_a"] is None and reciente["corregido_por"] is None
    assert primero["campos_corregidos"] == []
    assert cuerpo["integridad_verificada"] is True


def test_una_correccion_de_fecha_reubica_el_registro(cliente, repos):
    _cargar(repos, 84100, 200)
    con_error = _cargar(repos, 90000, 300)  # en realidad fue después del de 84.100 km
    _cargar(repos, 90000, 100, corrige=con_error, motivo="Fecha mal cargada.")

    intervenciones = _historial(cliente, repos).json()["intervenciones"]

    assert [i["kilometraje"] for i in intervenciones] == [90000, 90000, 84100]
    assert intervenciones[0]["campos_corregidos"] == ["fecha_intervencion"]


def test_el_ultimo_kilometraje_del_vehiculo_usa_el_valor_corregido(cliente, repos):
    con_error = _cargar(repos, 948100, 10)
    _cargar(repos, 98100, 10, corrige=con_error, motivo="Un dígito de más.")

    vehiculo = _historial(cliente, repos).json()["vehiculo"]

    assert vehiculo["ultima_lectura"]["kilometraje"] == 98100


def test_la_alerta_de_kilometraje_indica_contra_que_lectura_se_comparo(cliente, repos):
    _cargar(repos, 84100, 200)
    _cargar(repos, 48100, 70)

    alerta = _historial(cliente, repos).json()["intervenciones"][0]["alerta_kilometraje"]

    assert alerta["tipo"] == "kilometraje_inferior"
    assert alerta["kilometraje_anterior"] == 84100
    assert datetime.fromisoformat(alerta["fecha_anterior"]) == inicio_del_dia(hoy_en_argentina() - timedelta(days=200))


def test_informa_si_la_cadena_de_hash_fue_alterada(cliente, repos):
    for km, dias in ((84100, 200), (91800, 100), (98450, 10)):
        _cargar(repos, km, dias)
    assert _historial(cliente, repos).json()["integridad_verificada"] is True

    repos.intervenciones.intervenciones[1]["kilometraje"] = 59000

    assert _historial(cliente, repos).json()["integridad_verificada"] is False


def test_no_se_ve_el_historial_de_un_vehiculo_ajeno(cliente, repos):
    _cargar(repos, 84100, 200)
    otro_propietario = _token(ObjectId(), Rol.PROPIETARIO)

    respuesta = _historial(cliente, repos, headers=otro_propietario)

    assert respuesta.status_code == 404
    assert "intervenciones" not in respuesta.json()


def test_solo_lo_ve_un_propietario(cliente, repos):
    respuesta = _historial(cliente, repos, headers=_token(ObjectId(), Rol.TALLER))

    assert respuesta.status_code == 403
