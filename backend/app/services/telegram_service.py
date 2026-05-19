import asyncio
import logging
from collections import defaultdict

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_TELEGRAM_API_BASE = "https://api.telegram.org/bot{token}/{method}"

# Telegram enforces 1 msg/sec per chat; semaphores prevent bursting.
_chat_semaphores: dict[str, asyncio.Semaphore] = defaultdict(lambda: asyncio.Semaphore(1))


def _api_url(method: str) -> str:
    return _TELEGRAM_API_BASE.format(token=settings.TELEGRAM_BOT_TOKEN, method=method)


class TelegramService:
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(timeout=10.0)

    async def send_message(self, chat_id: str, text: str) -> bool:
        async with _chat_semaphores[chat_id]:
            try:
                response = await self._client.post(
                    _api_url("sendMessage"),
                    json={
                        "chat_id": chat_id,
                        "text": text,
                        "parse_mode": "HTML",
                    },
                )
                data = response.json()

                if not data.get("ok"):
                    logger.error(
                        "Telegram sendMessage failed | chat=%s error=%s",
                        chat_id,
                        data.get("description"),
                    )
                    return False

                logger.info("Telegram message sent | chat=%s", chat_id)
                return True

            except httpx.TimeoutException:
                logger.error("Telegram sendMessage timed out | chat=%s", chat_id)
                return False
            except Exception:
                logger.exception("Telegram sendMessage error | chat=%s", chat_id)
                return False

    async def close(self) -> None:
        await self._client.aclose()
