from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.errors import PyMongoError

from app.core.db import obtener_db

router = APIRouter(tags=["salud"])


@router.get("/salud")
async def salud(db: Annotated[AsyncDatabase, Depends(obtener_db)]):
    """Indica si la API responde y si llega a MongoDB."""
    try:
        await db.command("ping")
    except PyMongoError:
        return JSONResponse(
            status_code=503,
            content={"api": "ok", "base_de_datos": "sin_conexion"},
        )
    return {"api": "ok", "base_de_datos": "ok"}
