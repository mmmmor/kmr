"""Esquemas de intervenciones para los endpoints con sesión. La consulta pública (HU-010) tiene los suyos."""

import re
from datetime import date, datetime
from typing import Annotated

from pydantic import (
    AfterValidator,
    BaseModel,
    StringConstraints,
    ValidationInfo,
    field_validator,
    model_validator,
)

from app.core.fechas import hoy_en_argentina
from app.esquemas.vehiculos import Dominio, UltimaLectura
from app.modelos.intervencion import TIPOS_INTERVENCION, AlertaKilometraje, Origen

KM_MAXIMO = 2_000_000
CANTIDAD_MAXIMA = 9_999
MAX_ITEMS = 50


def _vacio_a_none(texto: str) -> str | None:
    return texto or None


# Textos opcionales: sin espacios en los extremos y, si quedan vacíos, None.
DescripcionOpcional = Annotated[
    str, StringConstraints(strip_whitespace=True, max_length=1000), AfterValidator(_vacio_a_none)
]
DetalleOpcional = Annotated[
    str, StringConstraints(strip_whitespace=True, max_length=200), AfterValidator(_vacio_a_none)
]


class ItemEntrada(BaseModel):
    descripcion: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
    cantidad: int

    @field_validator("cantidad")
    @classmethod
    def validar_cantidad(cls, cantidad: int) -> int:
        if not 1 <= cantidad <= CANTIDAD_MAXIMA:
            raise ValueError("Ingresá una cantidad entre 1 y 9.999.")
        return cantidad


class ProximaRevisionEntrada(BaseModel):
    kilometraje: int | None = None
    fecha: date | None = None
    detalle: DetalleOpcional | None = None

    @field_validator("kilometraje")
    @classmethod
    def validar_kilometraje(cls, kilometraje: int | None) -> int | None:
        if kilometraje is not None and not 0 < kilometraje <= KM_MAXIMO:
            raise ValueError("Ingresá un kilometraje entre 1 y 2.000.000 km.")
        return kilometraje

    @model_validator(mode="after")
    def exigir_kilometraje_o_fecha(self):
        # Sin kilometraje ni fecha no se puede calcular la alerta de servicio (HU-014).
        if self.kilometraje is None and self.fecha is None:
            raise ValueError("Indicá el kilometraje o la fecha de la próxima revisión.")
        return self


class IntervencionEntrada(BaseModel):
    """Datos del servicio, comunes a la carga del taller y a la del propietario."""

    fecha_intervencion: date
    kilometraje: int
    tipo: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    descripcion: DescripcionOpcional | None = None
    items: list[ItemEntrada]
    proxima_revision: ProximaRevisionEntrada | None = None

    @field_validator("fecha_intervencion")
    @classmethod
    def validar_fecha(cls, fecha: date) -> date:
        if fecha > hoy_en_argentina():
            raise ValueError("La fecha no puede ser posterior a hoy.")
        if fecha.year < 1900:
            raise ValueError("Ingresá una fecha válida.")
        return fecha

    @field_validator("kilometraje")
    @classmethod
    def validar_kilometraje(cls, kilometraje: int) -> int:
        if not 0 <= kilometraje <= KM_MAXIMO:
            raise ValueError("Ingresá un kilometraje entre 0 y 2.000.000 km.")
        return kilometraje

    @field_validator("tipo")
    @classmethod
    def validar_tipo(cls, tipo: str) -> str:
        if tipo not in TIPOS_INTERVENCION:
            raise ValueError("Elegí un tipo de intervención de la lista.")
        return tipo

    @field_validator("items")
    @classmethod
    def validar_items(cls, items: list[ItemEntrada]) -> list[ItemEntrada]:
        if not items:
            raise ValueError("Agregá al menos un ítem.")
        if len(items) > MAX_ITEMS:
            raise ValueError(f"Podés cargar hasta {MAX_ITEMS} ítems.")
        return items

    @field_validator("proxima_revision")
    @classmethod
    def validar_proxima_revision(cls, proxima, info: ValidationInfo):
        # info.data solo trae los campos anteriores que ya validaron bien.
        kilometraje, fecha = info.data.get("kilometraje"), info.data.get("fecha_intervencion")
        if proxima is None:
            return None
        if None not in (proxima.kilometraje, kilometraje) and proxima.kilometraje <= kilometraje:
            raise ValueError("El kilometraje de la próxima revisión tiene que ser mayor al del servicio.")
        if None not in (proxima.fecha, fecha) and proxima.fecha <= fecha:
            raise ValueError("La fecha de la próxima revisión tiene que ser posterior a la del servicio.")
        return proxima


class CorreccionEntrada(IntervencionEntrada):
    """Corrección vinculada (HU-011): los datos completos del registro ya corregidos y el motivo."""

    motivo: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]


# --- Taller (HU-007) ---


def validar_codigo(codigo: str) -> str:
    digitos = re.sub(r"\s", "", codigo)
    if not re.fullmatch(r"[0-9]{6}", digitos):
        raise ValueError("El código tiene 6 dígitos.")
    return digitos


CodigoIngresado = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=20),
    AfterValidator(validar_codigo),
]


class AutorizacionEntrada(BaseModel):
    dominio: Dominio
    codigo: CodigoIngresado


class IntervencionTallerEntrada(IntervencionEntrada):
    dominio: Dominio
    codigo: CodigoIngresado


# --- Salidas ---


class AutorizacionSalida(BaseModel):
    dominio: str
    marca: str
    modelo: str
    anio: int
    ultima_lectura: UltimaLectura | None


class ItemSalida(BaseModel):
    descripcion: str
    cantidad: int


class ProximaRevisionSalida(BaseModel):
    kilometraje: int | None
    fecha: datetime | None
    detalle: str | None


class AlertaKilometrajeSalida(BaseModel):
    """La inconsistencia y la lectura contra la que se comparó: "inferior al último registrado (84.100 km)"."""

    tipo: AlertaKilometraje
    kilometraje_anterior: int
    fecha_anterior: datetime


class IntervencionSalida(BaseModel):
    id: str
    dominio: str
    origen: Origen
    fecha_intervencion: datetime
    kilometraje: int
    tipo: str
    descripcion: str | None
    items: list[ItemSalida]
    proxima_revision: ProximaRevisionSalida | None
    tiene_comprobante: bool
    alerta_kilometraje: AlertaKilometrajeSalida | None
    fecha_registro: datetime
