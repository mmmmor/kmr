"""Esquemas de la consulta pública (HU-010). Propios, no reutilizan los de los endpoints con sesión.

Solo declaran lo que se puede mostrar sin cuenta: ningún dato del titular (nombre, correo, ids de
usuario), ni quién cargó cada registro, ni la descripción libre ni el archivo del comprobante, que
pueden tener datos personales. Pydantic descarta cualquier otro campo al armar la respuesta.
"""

from datetime import datetime

from pydantic import BaseModel

from app.esquemas.historial import RegistroVinculado
from app.esquemas.intervenciones import AlertaKilometrajeSalida, ItemSalida
from app.esquemas.vehiculos import UltimaLectura
from app.modelos.intervencion import Origen


class VehiculoPublico(BaseModel):
    dominio: str
    marca: str
    modelo: str
    anio: int


class IntervencionPublica(BaseModel):
    id: str
    fecha: datetime  # la del servicio; en una corrección, la del día en que se cargó
    fecha_intervencion: datetime
    kilometraje: int
    tipo: str
    items: list[ItemSalida]
    origen: Origen
    taller: str | None  # razón social del taller verificado
    alerta_kilometraje: AlertaKilometrajeSalida | None
    corrige_a: RegistroVinculado | None
    corregido_por: RegistroVinculado | None
    motivo_correccion: str | None
    campos_corregidos: list[str]
    tiene_comprobante: bool


class ConsultaPublicaSalida(BaseModel):
    dominio: str
    vehiculo: VehiculoPublico | None  # None si no hay registros (no se revela si el dominio tiene cuenta)
    integridad_verificada: bool
    ultima_lectura: UltimaLectura | None
    intervenciones: list[IntervencionPublica]  # del más reciente al más antiguo
