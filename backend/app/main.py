from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core import db
from app.core.config import obtener_settings
from app.routers import salud


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.conectar()
    yield
    await db.cerrar()


def crear_app() -> FastAPI:
    settings = obtener_settings()
    app = FastAPI(title="KmR API", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_url],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(salud.router, prefix="/api")
    return app


app = crear_app()
