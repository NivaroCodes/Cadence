_SEQUENCE_FRAMING: dict[int, str] = {
    1: (
        "This is follow-up #1 (sent ~3 days after the original email). "
        "Use a curiosity hook — ask a short, provocative question related to their business. "
        "Reference the previous email briefly but don't repeat its content. "
        "Be direct. No more than 80 words."
    ),
    2: (
        "This is follow-up #2 (sent ~7 days after the original email). "
        "This is the last outreach — frame it as such, lightly. "
        "Create mild urgency without pressure. "
        "One sentence referencing the previous emails, then a clear final CTA. "
        "No more than 60 words."
    ),
}

_LANGUAGE_INSTRUCTION: dict[str, str] = {
    "ru": "Write entirely in Russian (Русский язык).",
    "kz": "Write entirely in Kazakh (Қазақ тілі).",
    "en": "Write entirely in English.",
}


def build_followup_prompt(
    original_email: str,
    sequence: int,
    language: str,
) -> str:
    if sequence not in _SEQUENCE_FRAMING:
        raise ValueError(f"sequence must be 1 or 2, got {sequence}")
    if language not in _LANGUAGE_INSTRUCTION:
        raise ValueError(f"language must be one of ru/kz/en, got {language}")

    return (
        f"{_LANGUAGE_INSTRUCTION[language]}\n"
        f"{_SEQUENCE_FRAMING[sequence]}\n\n"
        f"Original email sent:\n"
        f"---\n"
        f"{original_email}\n"
        f"---\n\n"
        f"Write the follow-up message body only. No subject line."
    )
