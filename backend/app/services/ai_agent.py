import asyncio
import json
import logging
import time
from typing import Any

import google.generativeai as genai

from app.config import settings
from app.prompts.analyze import ANALYZE_SYSTEM_PROMPT, build_analyze_user_prompt
from app.prompts.email import build_email_prompt
from app.prompts.followup import build_followup_prompt

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
_BASE_BACKOFF = 2.0


def _configure_genai() -> None:
    genai.configure(api_key=settings.GEMINI_API_KEY)


def _with_retry(fn, *args, **kwargs) -> Any:
    """Exponential backoff on ResourceExhausted (429)."""
    last_exc: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            error_str = str(exc).lower()
            if "resource_exhausted" in error_str or "429" in error_str:
                delay = _BASE_BACKOFF ** attempt
                logger.warning("Gemini rate limited, retrying in %.1fs (attempt %d)", delay, attempt + 1)
                time.sleep(delay)
                last_exc = exc
            else:
                raise
    raise last_exc


class GeminiAgent:
    def __init__(self) -> None:
        _configure_genai()
        self._model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            system_instruction=ANALYZE_SYSTEM_PROMPT,
        )
        self._email_model = genai.GenerativeModel(model_name="gemini-2.5-flash")

    async def analyze_lead(self, lead_data: dict) -> dict:
        user_prompt = build_analyze_user_prompt(lead_data)
        logger.info("Analyzing lead: %s @ %s", lead_data.get("name"), lead_data.get("company"))

        def _call() -> dict:
            response = self._model.generate_content(
                user_prompt,
                generation_config=genai.types.GenerationConfig(
                    response_mime_type="application/json",
                    temperature=0.3,
                ),
            )
            return json.loads(response.text)

        try:
            result = await asyncio.to_thread(_with_retry, _call)
            logger.info("Lead analysis complete for %s", lead_data.get("company"))
            return result
        except Exception:
            logger.exception("Failed to analyze lead %s", lead_data.get("company"))
            raise

    async def generate_email(
        self,
        lead_analysis: dict,
        campaign_tone: str,
        language: str,
        lead_name: str | None = None,
        company_name: str | None = None,
    ) -> str:
        prompt = build_email_prompt(
            lead_analysis,
            campaign_tone,
            language,
            lead_name=lead_name,
            company_name=company_name,
        )
        logger.info("Generating email | tone=%s lang=%s", campaign_tone, language)

        def _call() -> str:
            response = self._email_model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(temperature=0.7),
            )
            return response.text.strip()

        try:
            result = await asyncio.to_thread(_with_retry, _call)
            logger.info("Email generated (%d chars)", len(result))
            return result
        except Exception:
            logger.exception("Failed to generate email")
            raise

    async def generate_followup(
        self,
        original_email: str,
        sequence: int,
        language: str,
        lead_name: str | None = None,
        company_name: str | None = None,
    ) -> str:
        prompt = build_followup_prompt(
            original_email,
            sequence,
            language,
            lead_name=lead_name,
            company_name=company_name,
        )
        logger.info("Generating follow-up | sequence=%d lang=%s", sequence, language)

        def _call() -> str:
            response = self._email_model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(temperature=0.6),
            )
            return response.text.strip()

        try:
            result = await asyncio.to_thread(_with_retry, _call)
            logger.info("Follow-up #%d generated (%d chars)", sequence, len(result))
            return result
        except Exception:
            logger.exception("Failed to generate follow-up #%d", sequence)
            raise
