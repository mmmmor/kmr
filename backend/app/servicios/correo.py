"""Envío de correos con la API transaccional de Brevo.

Sin BREVO_API_KEY o CORREO_REMITENTE (desarrollo local), el correo no se envía: se escribe en el
log de la API para poder probar el flujo. En producción las dos variables tienen que estar.
"""

import asyncio
import json
import logging
import urllib.request
from dataclasses import dataclass

from app.core.config import obtener_settings

URL_BREVO = "https://api.brevo.com/v3/smtp/email"
NOMBRE_REMITENTE = "KmR"

logger = logging.getLogger("kmr.correo")


@dataclass
class Correo:
    destinatario: str
    nombre: str
    asunto: str
    html: str
    texto: str


class EnviadorBrevo:
    def __init__(self, api_key: str, remitente: str):
        self._api_key = api_key
        self._remitente = remitente

    async def enviar(self, correo: Correo) -> None:
        cuerpo = json.dumps({
            "sender": {"name": NOMBRE_REMITENTE, "email": self._remitente},
            "to": [{"email": correo.destinatario, "name": correo.nombre}],
            "subject": correo.asunto,
            "htmlContent": correo.html,
            "textContent": correo.texto,
        }).encode("utf-8")
        pedido = urllib.request.Request(
            URL_BREVO,
            data=cuerpo,
            method="POST",
            headers={"api-key": self._api_key, "content-type": "application/json", "accept": "application/json"},
        )
        # urllib es bloqueante: se ejecuta en un hilo para no frenar al resto de la API.
        await asyncio.to_thread(urllib.request.urlopen, pedido, timeout=10)


class EnviadorConsola:
    """Solo para desarrollo: deja el correo en el log en lugar de enviarlo."""

    async def enviar(self, correo: Correo) -> None:
        logger.warning(
            "BREVO_API_KEY o CORREO_REMITENTE sin configurar: el correo a %s no se envió.\n%s",
            correo.destinatario,
            correo.texto,
        )


def obtener_enviador() -> EnviadorBrevo | EnviadorConsola:
    settings = obtener_settings()
    if settings.brevo_api_key and settings.correo_remitente:
        return EnviadorBrevo(settings.brevo_api_key, settings.correo_remitente)
    return EnviadorConsola()
