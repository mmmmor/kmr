"""Alta interna del administrador (no hay registro público para este rol).

Uso, desde backend/:
    python -m scripts.crear_admin --correo admin@kmr.com.ar --nombre Ana --apellido López

La contraseña se pide por consola sin mostrarla. Para automatizar, se puede pasar en la
variable de entorno ADMIN_CONTRASENA. Usa la conexión de MONGODB_URI (backend/.env).
"""

import argparse
import asyncio
import getpass
import os
import sys

from app.core import db
from app.esquemas.auth import RegistroEntrada
from app.modelos.usuario import Rol
from app.repositorios.usuarios import CorreoYaRegistrado, RepositorioUsuarios
from app.servicios.auth import nuevo_usuario
from pydantic import ValidationError


def pedir_contrasena() -> str:
    if contrasena := os.environ.get("ADMIN_CONTRASENA"):
        return contrasena
    contrasena = getpass.getpass("Contraseña: ")
    if getpass.getpass("Repetí la contraseña: ") != contrasena:
        sys.exit("Las contraseñas no coinciden.")
    return contrasena


async def crear_admin(datos: RegistroEntrada) -> str:
    db.conectar()
    try:
        base = db.obtener_db()
        await db.crear_indices(base)
        return str(await RepositorioUsuarios(base).insertar(nuevo_usuario(datos, Rol.ADMINISTRADOR)))
    finally:
        await db.cerrar()


def main() -> None:
    parser = argparse.ArgumentParser(description="Crea la cuenta del administrador de KmR.")
    parser.add_argument("--correo", required=True)
    parser.add_argument("--nombre", required=True)
    parser.add_argument("--apellido", required=True)
    argumentos = parser.parse_args()

    try:
        # Mismas validaciones que el registro: correo válido y política de contraseñas.
        datos = RegistroEntrada(
            nombre=argumentos.nombre,
            apellido=argumentos.apellido,
            correo=argumentos.correo,
            contrasena=pedir_contrasena(),
        )
    except ValidationError as error:
        sys.exit("\n".join(f"{e['loc'][0]}: {e['msg'].removeprefix('Value error, ')}" for e in error.errors()))

    try:
        usuario_id = asyncio.run(crear_admin(datos))
    except CorreoYaRegistrado:
        sys.exit(f"Ya existe una cuenta con el correo {datos.correo}.")
    print(f"Administrador creado: {datos.correo} (id {usuario_id}).")


if __name__ == "__main__":
    main()
