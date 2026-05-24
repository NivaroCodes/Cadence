import enum


class CampaignTone(str, enum.Enum):
    professional = "professional"
    casual = "casual"


class Language(str, enum.Enum):
    ru = "ru"
    kz = "kz"
    en = "en"


_LANGUAGE_INSTRUCTION: dict[Language, str] = {
    Language.ru: "Write the entire email in Russian (Русский язык).",
    Language.kz: "Write the entire email in Kazakh (Қазақ тілі).",
    Language.en: "Write the entire email in English.",
}

_TONE_INSTRUCTION: dict[CampaignTone, str] = {
    CampaignTone.professional: (
        "Tone: formal and professional. "
        "Address the recipient respectfully, use business language."
    ),
    CampaignTone.casual: (
        "Tone: warm and conversational. "
        "Write as one founder to another — direct, human, no corporate fluff."
    ),
}


def build_email_prompt(
    analysis: dict,
    tone: str,
    language: str,
    lead_name: str | None = None,
    company_name: str | None = None,
) -> str:
    tone_enum = CampaignTone(tone)
    lang_enum = Language(language)

    pain_points = ", ".join(analysis.get("pain_points", []))
    company = company_name or "your company"
    recipient_name = lead_name or ""

    return (
        f"{_LANGUAGE_INSTRUCTION[lang_enum]}\n"
        f"{_TONE_INSTRUCTION[tone_enum]}\n\n"
        f"Write a cold outreach email using this lead intelligence:\n"
        f"- Recipient Name: {recipient_name}\n"
        f"- Company: {company}\n"
        f"- Industry: {analysis.get('industry', 'unknown')}\n"
        f"- Company size: {analysis.get('company_size', 'unknown')}\n"
        f"- Decision maker: {analysis.get('decision_maker_role', 'unknown')}\n"
        f"- Pain points: {pain_points}\n"
        f"- Budget signals: {analysis.get('budget_signals', 'unknown')}\n\n"
        f"Constraints:\n"
        f"- Maximum 150 words\n"
        f"- One clear, specific call-to-action at the end\n"
        f"- No subject line — body only\n"
        f"- No generic phrases like 'I hope this email finds you well'\n"
        f"- Reference a specific pain point naturally in the opening\n"
        f"- Do not mention you used AI to write this\n"
        f"- CRITICAL: Never use placeholder text like [CEO Name], [Company Name], [My Name], [My Title]. "
        f"If you don't know the CEO name, use a neutral greeting like 'Hi there,' or 'Hi {company} team,'. "
        f"Replace [Company Name] with the actual company name from context: {company}. "
        f"Sign the email as 'The Cadence Team'.\n"
    )
