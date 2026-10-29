"""Rol de base de datos con el que se conecta la API (`kmr_app`).

Es la barrera de la inmutabilidad en la propia base: sobre `intervenciones` solo permite leer e
insertar, así que MongoDB rechaza cualquier modificación o borrado aunque la API tuviera un error.
En el resto de las colecciones da lo que la API usa. Los tests de integración lo crean desde acá
y corren la API con un usuario que solo tiene este rol.

En Atlas se crea a mano (Database & Network Access → Custom Roles). Para ver la lista de acciones
por colección, desde backend/:
    python -m scripts.rol_app --base kmr
"""

import argparse

NOMBRE = "kmr_app"

# Colección → acciones. createCollection y createIndex: la API crea las colecciones y los índices al arrancar.
PERMISOS = {
    "intervenciones": ["find", "insert", "createIndex", "createCollection"],
    "usuarios": ["find", "insert", "update", "createIndex", "createCollection"],
    "talleres": ["find", "insert", "update", "createIndex", "createCollection"],
    "vehiculos": ["find", "insert", "update", "createIndex", "createCollection"],
    "codigos_autorizacion": ["find", "insert", "update", "createIndex", "createCollection"],
    "tokens_recuperacion": ["find", "insert", "update", "createIndex", "createCollection"],
    # GridFS: borra el archivo si el registro de la intervención falla, y revisa sus índices antes de escribir.
    "comprobantes.files": ["find", "insert", "remove", "createIndex", "createCollection", "listIndexes"],
    "comprobantes.chunks": ["find", "insert", "remove", "createIndex", "createCollection", "listIndexes"],
}


def privilegios(base: str) -> list[dict]:
    """Los permisos en el formato de createRole, para la base indicada."""
    return [
        {"resource": {"db": base, "collection": coleccion}, "actions": acciones}
        for coleccion, acciones in PERMISOS.items()
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=f"Muestra las acciones del rol {NOMBRE} por colección.")
    parser.add_argument("--base", default="kmr")
    base = parser.parse_args().base
    print(f"Rol {NOMBRE}:")
    for coleccion, acciones in PERMISOS.items():
        print(f"  {base}.{coleccion}: {', '.join(acciones)}")


if __name__ == "__main__":
    main()
