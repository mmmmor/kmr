"""Dependencias de FastAPI compartidas por los routers. En los tests se reemplazan por versiones en memoria."""

from typing import Annotated

from fastapi import Depends
from pymongo.asynchronous.database import AsyncDatabase

from app.core import db as conexion
from app.core.db import obtener_db
from app.repositorios.codigos import RepositorioCodigos
from app.repositorios.comprobantes import AlmacenComprobantes
from app.repositorios.intervenciones import RepositorioIntervenciones
from app.repositorios.talleres import RepositorioTalleres
from app.repositorios.usuarios import RepositorioUsuarios
from app.repositorios.vehiculos import RepositorioVehiculos


def obtener_repositorio_usuarios(
    db: Annotated[AsyncDatabase, Depends(obtener_db)],
) -> RepositorioUsuarios:
    return RepositorioUsuarios(db)


def obtener_repositorio_talleres(
    db: Annotated[AsyncDatabase, Depends(obtener_db)],
) -> RepositorioTalleres:
    return RepositorioTalleres(db)


def obtener_repositorio_vehiculos(
    db: Annotated[AsyncDatabase, Depends(obtener_db)],
) -> RepositorioVehiculos:
    return RepositorioVehiculos(db)


def obtener_repositorio_codigos(
    db: Annotated[AsyncDatabase, Depends(obtener_db)],
) -> RepositorioCodigos:
    return RepositorioCodigos(db)


def obtener_repositorio_intervenciones(
    db: Annotated[AsyncDatabase, Depends(obtener_db)],
) -> RepositorioIntervenciones:
    return RepositorioIntervenciones(db)


def obtener_almacen_comprobantes(
    db: Annotated[AsyncDatabase, Depends(obtener_db)],
) -> AlmacenComprobantes:
    return AlmacenComprobantes(db)


def obtener_transaccion():
    return conexion.en_transaccion
