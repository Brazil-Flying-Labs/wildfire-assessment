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


ERROR_TRANSLATIONS = {
    "en": {
        "error.no_permission_create": "You do not have permission to create areas of interest in this country.",
        "error.no_permission_update": "You do not have permission to update this area.",
        "error.no_permission_move": "You do not have permission to move areas to this country.",
        "error.no_permission_delete": "You do not have permission to delete this area.",
        "error.duplicate_name": "An area of interest with this name already exists in the selected country.",
        "error.geojson_not_object": "GeoJSON must be an object.",
        "error.geojson_no_type": "GeoJSON must have a 'type' field.",
        "error.feature_no_geometry": "Feature must have a 'geometry' field.",
        "error.featurecollection_empty": "FeatureCollection must have at least one feature.",
        "error.feature_not_object": "Feature at index {index} must be an object.",
        "error.unsupported_geometry": "Unsupported geometry type: '{geom_type}'. Only Polygon or MultiPolygon geometries are accepted.",
        "error.unsupported_geojson_type": "Unsupported GeoJSON type: '{geojson_type}'. Must be Feature, FeatureCollection, or a geometry type.",
        "error.geometry_not_object": "{context}: Geometry must be an object.",
        "error.geometry_no_type": "{context}: Geometry must have a 'type' field.",
        "error.geometry_unsupported": "{context}: Unsupported geometry type '{geom_type}'. Only Polygon or MultiPolygon geometries are accepted.",
        "error.geometry_no_coordinates": "{context}: Geometry must have 'coordinates' field.",
        "error.geometry_invalid_structure": "{context}: Invalid geometry structure - {detail}",
        "error.geometry_invalid": "{context}: Invalid geometry - {detail}",
        "error.geometry_empty": "{context}: Geometry cannot be empty.",
        "error.longitude_out_of_range": "{context}: Longitude {value} is out of range [-180, 180].",
        "error.latitude_out_of_range": "{context}: Latitude {value} is out of range [-90, 90].",
        "error.ring_not_closed": "{context}: Linear ring is not closed. The first and last positions must be identical.",
        "error.ring_too_few_positions": "{context}: Linear ring must have at least 4 positions (3 distinct vertices plus a closure point).",
        "error.nested_geometry_collection": "{context}: GeometryCollections cannot contain other GeometryCollections (RFC 7946).",
        "error.invalid_deliverable": "Invalid deliverable type",
        "error.ai_empty_response": "AI analysis returned empty response",
        "error.ai_failed": "Failed to generate analysis: {detail}",
        "error.ai_followup_empty": "AI returned empty response",
        "error.ai_followup_failed": "Failed to generate response: {detail}",
    },
    "pt-BR": {
        "error.no_permission_create": "Você não tem permissão para criar áreas de interesse neste país.",
        "error.no_permission_update": "Você não tem permissão para atualizar esta área.",
        "error.no_permission_move": "Você não tem permissão para mover áreas para este país.",
        "error.no_permission_delete": "Você não tem permissão para excluir esta área.",
        "error.duplicate_name": "Já existe uma área de interesse com esse nome no país selecionado.",
        "error.geojson_not_object": "O GeoJSON deve ser um objeto.",
        "error.geojson_no_type": "O GeoJSON deve ter um campo 'type'.",
        "error.feature_no_geometry": "O Feature deve ter um campo 'geometry'.",
        "error.featurecollection_empty": "O FeatureCollection deve ter pelo menos um feature.",
        "error.feature_not_object": "O feature no índice {index} deve ser um objeto.",
        "error.unsupported_geometry": "Tipo de geometria não suportado: '{geom_type}'. Somente geometrias Polygon ou MultiPolygon são aceitas.",
        "error.unsupported_geojson_type": "Tipo de GeoJSON não suportado: '{geojson_type}'. Deve ser Feature, FeatureCollection ou um tipo de geometria.",
        "error.geometry_not_object": "{context}: A geometria deve ser um objeto.",
        "error.geometry_no_type": "{context}: A geometria deve ter um campo 'type'.",
        "error.geometry_unsupported": "{context}: Tipo de geometria não suportado '{geom_type}'. Somente geometrias Polygon ou MultiPolygon são aceitas.",
        "error.geometry_no_coordinates": "{context}: A geometria deve ter um campo 'coordinates'.",
        "error.geometry_invalid_structure": "{context}: Estrutura de geometria inválida - {detail}",
        "error.geometry_invalid": "{context}: Geometria inválida - {detail}",
        "error.geometry_empty": "{context}: A geometria não pode estar vazia.",
        "error.longitude_out_of_range": "{context}: Longitude {value} está fora do intervalo [-180, 180].",
        "error.latitude_out_of_range": "{context}: Latitude {value} está fora do intervalo [-90, 90].",
        "error.ring_not_closed": "{context}: O anel linear não está fechado. A primeira e a última posições devem ser idênticas.",
        "error.ring_too_few_positions": "{context}: O anel linear deve ter pelo menos 4 posições (3 vértices distintos mais o ponto de fechamento).",
        "error.nested_geometry_collection": "{context}: GeometryCollections não podem conter outras GeometryCollections (RFC 7946).",
        "error.invalid_deliverable": "Tipo de produto inválido",
        "error.ai_empty_response": "A análise de IA retornou uma resposta vazia",
        "error.ai_failed": "Falha ao gerar análise: {detail}",
        "error.ai_followup_empty": "A IA retornou uma resposta vazia",
        "error.ai_followup_failed": "Falha ao gerar resposta: {detail}",
    },
    "fr": {
        "error.no_permission_create": "Vous n'avez pas la permission de créer des zones d'intérêt dans ce pays.",
        "error.no_permission_update": "Vous n'avez pas la permission de modifier cette zone.",
        "error.no_permission_move": "Vous n'avez pas la permission de déplacer des zones vers ce pays.",
        "error.no_permission_delete": "Vous n'avez pas la permission de supprimer cette zone.",
        "error.duplicate_name": "Une zone d'intérêt portant ce nom existe déjà dans le pays sélectionné.",
        "error.geojson_not_object": "Le GeoJSON doit être un objet.",
        "error.geojson_no_type": "Le GeoJSON doit avoir un champ 'type'.",
        "error.feature_no_geometry": "Le Feature doit avoir un champ 'geometry'.",
        "error.featurecollection_empty": "Le FeatureCollection doit contenir au moins un feature.",
        "error.feature_not_object": "Le feature à l'index {index} doit être un objet.",
        "error.unsupported_geometry": "Type de géométrie non pris en charge : '{geom_type}'. Seules les géométries Polygon ou MultiPolygon sont acceptées.",
        "error.unsupported_geojson_type": "Type de GeoJSON non pris en charge : '{geojson_type}'. Doit être Feature, FeatureCollection ou un type de géométrie.",
        "error.geometry_not_object": "{context} : La géométrie doit être un objet.",
        "error.geometry_no_type": "{context} : La géométrie doit avoir un champ 'type'.",
        "error.geometry_unsupported": "{context} : Type de géométrie non pris en charge '{geom_type}'. Seules les géométries Polygon ou MultiPolygon sont acceptées.",
        "error.geometry_no_coordinates": "{context} : La géométrie doit avoir un champ 'coordinates'.",
        "error.geometry_invalid_structure": "{context} : Structure de géométrie invalide - {detail}",
        "error.geometry_invalid": "{context} : Géométrie invalide - {detail}",
        "error.geometry_empty": "{context} : La géométrie ne peut pas être vide.",
        "error.longitude_out_of_range": "{context} : La longitude {value} est hors de la plage [-180, 180].",
        "error.latitude_out_of_range": "{context} : La latitude {value} est hors de la plage [-90, 90].",
        "error.ring_not_closed": "{context} : L'anneau linéaire n'est pas fermé. La première et la dernière positions doivent être identiques.",
        "error.ring_too_few_positions": "{context} : L'anneau linéaire doit avoir au moins 4 positions (3 sommets distincts plus le point de fermeture).",
        "error.nested_geometry_collection": "{context} : Les GeometryCollections ne peuvent pas contenir d'autres GeometryCollections (RFC 7946).",
        "error.invalid_deliverable": "Type de livrable invalide",
        "error.ai_empty_response": "L'analyse IA a renvoyé une réponse vide",
        "error.ai_failed": "Échec de la génération de l'analyse : {detail}",
        "error.ai_followup_empty": "L'IA a renvoyé une réponse vide",
        "error.ai_followup_failed": "Échec de la génération de la réponse : {detail}",
    },
}


def get_user_language(request) -> str:
    """Get the user's preferred language from their profile, defaulting to 'en'."""
    if request and hasattr(request, "user") and request.user.is_authenticated:
        profile = getattr(request.user, "profile", None)
        if profile:
            return profile.default_language
    return "en"


def get_error_translation(language: str, key: str, **kwargs) -> str:
    """
    Get a translated error string.

    Args:
        language: Language code (en, pt-BR, fr)
        key: Translation key (e.g., 'error.duplicate_name')
        **kwargs: Format parameters for the message

    Returns:
        Translated and formatted string, falls back to English.
    """
    translations = ERROR_TRANSLATIONS.get(language, ERROR_TRANSLATIONS["en"])
    template = translations.get(key, ERROR_TRANSLATIONS["en"].get(key, key))
    if kwargs:
        return template.format(**kwargs)
    return template


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
