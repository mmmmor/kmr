from enum import StrEnum


class EstadoCodigo(StrEnum):
    """Estados guardados. "Vencido" no se guarda: es un código vigente cuya fecha de vencimiento pasó."""

    VIGENTE = "vigente"
    UTILIZADO = "utilizado"
    INVALIDADO = "invalidado"
