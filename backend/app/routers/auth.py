from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.asynchronous.database import AsyncDatabase

from app.core.db import obtener_db
from app.esquemas.auth import RegistroEntrada, UsuarioSalida
from app.repositorios.usuarios import CorreoYaRegistrado, RepositorioUsuarios
from app.servicios import auth as servicio_auth

router = APIRouter(prefix="/auth", tags=["auth"])


def obtener_repositorio_usuarios(
    db: Annotated[AsyncDatabase, Depends(obtener_db)],
) -> RepositorioUsuarios:
    return RepositorioUsuarios(db)


@router.post("/registro", status_code=status.HTTP_201_CREATED)
async def registro(
    datos: RegistroEntrada,
    repo: Annotated[RepositorioUsuarios, Depends(obtener_repositorio_usuarios)],
) -> UsuarioSalida:
    """Alta de propietario (HU-001)."""
    try:
        return await servicio_auth.registrar_propietario(datos, repo)
    except CorreoYaRegistrado:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una cuenta con ese correo electrónico.",
        )
