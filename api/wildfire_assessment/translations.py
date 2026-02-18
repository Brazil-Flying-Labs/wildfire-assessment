"""
Email translations for the Wildfire Assessment platform.

Translations follow the same language codes as the UI:
- en: English
- pt-BR: Português (Brasil)
- fr: Français
"""

EMAIL_TRANSLATIONS = {
    "en": {
        "email.subject": "Wildfire Analyser - Scientific Deliverable Ready",
        "email.body": (
            "The scientific deliverable '{reserve_name}' is ready for download on"
            " this link: {url}"
        ),
    },
    "pt-BR": {
        "email.subject": "Wildfire Analyser - Produto Científico Pronto",
        "email.body": (
            "O produto científico '{reserve_name}' está pronto para download"
            " neste link: {url}"
        ),
    },
    "fr": {
        "email.subject": "Wildfire Analyser - Livrable Scientifique Prêt",
        "email.body": (
            "Le livrable scientifique '{reserve_name}' est prêt à être téléchargé"
            " via ce lien : {url}"
        ),
    },
}


def get_email_translation(language: str, key: str) -> str:
    """
    Get a translated email string for the given language and key.

    Args:
        language: Language code (en, pt-BR, fr)
        key: Translation key (e.g., 'email.subject', 'email.body')

    Returns:
        Translated string, falls back to English if language not found.
    """
    translations = EMAIL_TRANSLATIONS.get(language, EMAIL_TRANSLATIONS["en"])
    return translations.get(key, EMAIL_TRANSLATIONS["en"].get(key, key))
