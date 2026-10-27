from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.core import db
from app.core.config import obtener_settings
from app.core.errores import ErrorDeCampo, manejar_error_de_campo, manejar_error_validacion
from app.routers import auth, salud, talleres


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.conectar()
    await db.crear_indices(db.obtener_db())
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
    app.add_exception_handler(RequestValidationError, manejar_error_validacion)
    app.add_exception_handler(ErrorDeCampo, manejar_error_de_campo)
    app.include_router(salud.router, prefix="/api")
    app.include_router(auth.router, prefix="/api")
    app.include_router(talleres.router, prefix="/api")
    return app


app = crear_app()
