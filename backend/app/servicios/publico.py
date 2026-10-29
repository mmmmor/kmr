"""Consulta pública del historial por dominio (HU-010), sin datos personales del titular."""

from app.esquemas.publico import ConsultaPublicaSalida, IntervencionPublica, VehiculoPublico
from app.esquemas.vehiculos import UltimaLectura
from app.repositorios.intervenciones import RepositorioIntervenciones
from app.repositorios.talleres import RepositorioTalleres
from app.repositorios.vehiculos import RepositorioVehiculos
from app.servicios import historial, kilometraje
from app.servicios.hash import verificar_cadena


async def consultar(
    dominio: str,
    vehiculos: RepositorioVehiculos,
    intervenciones: RepositorioIntervenciones,
    talleres: RepositorioTalleres,
) -> ConsultaPublicaSalida:
    """`dominio` ya normalizado. Un dominio sin cuenta y uno sin registros responden igual."""
    vehiculo = await vehiculos.buscar_por_dominio(dominio)
    registros = await intervenciones.listar_por_vehiculo(vehiculo["_id"]) if vehiculo else []
    if not registros:
        return ConsultaPublicaSalida(
            dominio=dominio, vehiculo=None, integridad_verificada=True, ultima_lectura=None, intervenciones=[]
        )

    salidas = historial.salidas(
        registros,
        {vehiculo["_id"]: vehiculo["dominio"]},
        await historial.razones_sociales(registros, talleres),
        kilometraje.referencias(registros),
    )
    ultima = kilometraje.ultima_lectura(registros)
    return ConsultaPublicaSalida(
        dominio=dominio,
        vehiculo=VehiculoPublico.model_validate(vehiculo),
        integridad_verificada=verificar_cadena(registros),
        ultima_lectura=UltimaLectura(kilometraje=ultima["kilometraje"], fecha=ultima["fecha_intervencion"]),
        # Se valida contra el esquema público: los campos que no declara quedan afuera.
        intervenciones=[IntervencionPublica.model_validate(s.model_dump()) for s in salidas],
    )
