"""
Email translations for the Wildfire Assessment platform.

Translations follow the same language codes as the UI:
- en: English
- pt-BR: Português (Brasil)
- fr: Français
- es-ES: Español (España)
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
    "es-ES": {
        "email.subject": "Wildfire Analyser - Producto Científico Listo",
        "email.body": (
            "El producto científico '{reserve_name}' está listo para descargar"
            " en este enlace: {url}"
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
        "error.coordinates_3d": "{context}: 3D coordinates are not supported. Please remove the Z (altitude) values from your GeoJSON file.",
        "error.position_too_few_elements": "{context}: Position must have at least 2 elements [longitude, latitude].",
        "error.position_not_all_numbers": "{context}: Position elements must all be numbers.",
        "error.fc_feature_missing_type": "Feature at index {index} must have type 'Feature'.",
        "error.feature_no_properties": "{context}: Feature must have a 'properties' field (can be null or an empty object).",
        "error.fc_feature_no_geometry": "Feature at index {index} must have a non-null 'geometry' field.",
        "error.feature_invalid_id": "{context}: Feature 'id' must be a string or number.",
        "error.bbox_invalid_length": "Bounding box must be an array of exactly 4 numbers [west, south, east, north].",
        "error.bbox_latitude_out_of_range": "Bounding box latitude values must be between -90 and 90.",
        "error.invalid_deliverable": "Invalid deliverable type",
        "error.area_too_large": "The area of interest exceeds the maximum allowed size of {max_ha} hectares. Please upload a smaller polygon.",
        "error.degenerate_multipolygon_part": "{context}: Polygon #{index} inside the MultiPolygon is too small ({area} m², minimum {threshold} m²) and is likely a digitization artifact. Please remove the stray polygon from your GeoJSON file and upload only the intended area.",
        "error.ai_empty_response": "AI analysis returned empty response",
        "error.ai_failed": "Failed to generate analysis: {detail}",
        "error.ai_followup_empty": "AI returned empty response",
        "error.ai_followup_failed": "Failed to generate response: {detail}",
        "error.ai_disabled": "AI analysis is currently disabled.",
                "error.no_satellite_imagery": "No satellite imagery was found for the selected dates and filters. Try adjusting your settings: use dates further in the past, increase the cloud threshold, or extend the days before/after range.",
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
        "error.coordinates_3d": "{context}: Coordenadas 3D não são suportadas. Por favor, remova os valores Z (altitude) do seu arquivo GeoJSON.",
        "error.position_too_few_elements": "{context}: A posição deve ter pelo menos 2 elementos [longitude, latitude].",
        "error.position_not_all_numbers": "{context}: Os elementos da posição devem ser todos números.",
        "error.fc_feature_missing_type": "O feature no índice {index} deve ter type 'Feature'.",
        "error.feature_no_properties": "{context}: O Feature deve ter um campo 'properties' (pode ser null ou um objeto vazio).",
        "error.fc_feature_no_geometry": "O feature no índice {index} deve ter um campo 'geometry' não nulo.",
        "error.feature_invalid_id": "{context}: O 'id' do Feature deve ser uma string ou número.",
        "error.bbox_invalid_length": "O bounding box deve ser um array de exatamente 4 números [oeste, sul, leste, norte].",
        "error.bbox_latitude_out_of_range": "Os valores de latitude do bounding box devem estar entre -90 e 90.",
        "error.invalid_deliverable": "Tipo de produto inválido",
        "error.area_too_large": "A área de interesse excede o tamanho máximo permitido de {max_ha} hectares. Por favor, envie um polígono menor.",
        "error.degenerate_multipolygon_part": "{context}: O polígono nº {index} dentro do MultiPolygon é pequeno demais ({area} m², mínimo {threshold} m²) e provavelmente é um artefato de digitalização. Por favor, remova o polígono extra do seu arquivo GeoJSON e envie apenas a área pretendida.",
        "error.ai_empty_response": "A análise de IA retornou uma resposta vazia",
        "error.ai_failed": "Falha ao gerar análise: {detail}",
        "error.ai_followup_empty": "A IA retornou uma resposta vazia",
        "error.ai_followup_failed": "Falha ao gerar resposta: {detail}",
        "error.ai_disabled": "A análise por IA está desativada no momento.",
        "error.no_satellite_imagery": "Nenhuma imagem de satélite foi encontrada para as datas e filtros selecionados. Tente ajustar suas configurações: use datas mais no passado, aumente o limite de nuvens ou amplie o intervalo de dias antes/depois.",
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
        "error.coordinates_3d": "{context} : Les coordonnées 3D ne sont pas prises en charge. Veuillez supprimer les valeurs Z (altitude) de votre fichier GeoJSON.",
        "error.position_too_few_elements": "{context} : La position doit avoir au moins 2 éléments [longitude, latitude].",
        "error.position_not_all_numbers": "{context} : Les éléments de la position doivent tous être des nombres.",
        "error.fc_feature_missing_type": "Le feature à l'index {index} doit avoir le type 'Feature'.",
        "error.feature_no_properties": "{context} : Le Feature doit avoir un champ 'properties' (peut être null ou un objet vide).",
        "error.fc_feature_no_geometry": "Le feature à l'index {index} doit avoir un champ 'geometry' non nul.",
        "error.feature_invalid_id": "{context} : L'identifiant du Feature doit être une chaîne ou un nombre.",
        "error.bbox_invalid_length": "Le bounding box doit être un tableau de exactement 4 nombres [ouest, sud, est, nord].",
        "error.bbox_latitude_out_of_range": "Les valeurs de latitude du bounding box doivent être entre -90 et 90.",
        "error.invalid_deliverable": "Type de livrable invalide",
        "error.area_too_large": "La zone d'intérêt dépasse la taille maximale autorisée de {max_ha} hectares. Veuillez télécharger un polygone plus petit.",
        "error.degenerate_multipolygon_part": "{context} : Le polygone n°{index} à l'intérieur du MultiPolygon est trop petit ({area} m², minimum {threshold} m²) et est probablement un artefact de numérisation. Veuillez retirer le polygone parasite de votre fichier GeoJSON et ne télécharger que la zone souhaitée.",
        "error.ai_empty_response": "L'analyse IA a renvoyé une réponse vide",
        "error.ai_failed": "Échec de la génération de l'analyse : {detail}",
        "error.ai_followup_empty": "L'IA a renvoyé une réponse vide",
        "error.ai_followup_failed": "Échec de la génération de la réponse : {detail}",
        "error.ai_disabled": "L'analyse par IA est actuellement désactivée.",
        "error.no_satellite_imagery": "Aucune image satellite n'a été trouvée pour les dates et filtres sélectionnés. Essayez d'ajuster vos paramètres : utilisez des dates plus anciennes, augmentez le seuil de nuages ou élargissez la plage de jours avant/après.",
    },
    "es-ES": {
        "error.no_permission_create": "No tiene permiso para crear áreas de interés en este país.",
        "error.no_permission_update": "No tiene permiso para actualizar esta área.",
        "error.no_permission_move": "No tiene permiso para mover áreas a este país.",
        "error.no_permission_delete": "No tiene permiso para eliminar esta área.",
        "error.duplicate_name": "Ya existe un área de interés con este nombre en el país seleccionado.",
        "error.geojson_not_object": "El GeoJSON debe ser un objeto.",
        "error.geojson_no_type": "El GeoJSON debe tener un campo 'type'.",
        "error.feature_no_geometry": "El Feature debe tener un campo 'geometry'.",
        "error.featurecollection_empty": "El FeatureCollection debe tener al menos un feature.",
        "error.feature_not_object": "El feature en el índice {index} debe ser un objeto.",
        "error.unsupported_geometry": "Tipo de geometría no soportado: '{geom_type}'. Solo se aceptan geometrías Polygon o MultiPolygon.",
        "error.unsupported_geojson_type": "Tipo de GeoJSON no soportado: '{geojson_type}'. Debe ser Feature, FeatureCollection o un tipo de geometría.",
        "error.geometry_not_object": "{context}: La geometría debe ser un objeto.",
        "error.geometry_no_type": "{context}: La geometría debe tener un campo 'type'.",
        "error.geometry_unsupported": "{context}: Tipo de geometría no soportado '{geom_type}'. Solo se aceptan geometrías Polygon o MultiPolygon.",
        "error.geometry_no_coordinates": "{context}: La geometría debe tener un campo 'coordinates'.",
        "error.geometry_invalid_structure": "{context}: Estructura de geometría inválida - {detail}",
        "error.geometry_invalid": "{context}: Geometría inválida - {detail}",
        "error.geometry_empty": "{context}: La geometría no puede estar vacía.",
        "error.longitude_out_of_range": "{context}: La longitud {value} está fuera del rango [-180, 180].",
        "error.latitude_out_of_range": "{context}: La latitud {value} está fuera del rango [-90, 90].",
        "error.ring_not_closed": "{context}: El anillo lineal no está cerrado. La primera y la última posición deben ser idénticas.",
        "error.ring_too_few_positions": "{context}: El anillo lineal debe tener al menos 4 posiciones (3 vértices distintos más el punto de cierre).",
        "error.nested_geometry_collection": "{context}: Las GeometryCollections no pueden contener otras GeometryCollections (RFC 7946).",
        "error.coordinates_3d": "{context}: Las coordenadas 3D no son soportadas. Por favor, elimine los valores Z (altitud) de su archivo GeoJSON.",
        "error.position_too_few_elements": "{context}: La posición debe tener al menos 2 elementos [longitud, latitud].",
        "error.position_not_all_numbers": "{context}: Los elementos de la posición deben ser todos números.",
        "error.fc_feature_missing_type": "El feature en el índice {index} debe tener type 'Feature'.",
        "error.feature_no_properties": "{context}: El Feature debe tener un campo 'properties' (puede ser null o un objeto vacío).",
        "error.fc_feature_no_geometry": "El feature en el índice {index} debe tener un campo 'geometry' no nulo.",
        "error.feature_invalid_id": "{context}: El 'id' del Feature debe ser una cadena o un número.",
        "error.bbox_invalid_length": "El bounding box debe ser un array de exactamente 4 números [oeste, sur, este, norte].",
        "error.bbox_latitude_out_of_range": "Los valores de latitud del bounding box deben estar entre -90 y 90.",
        "error.invalid_deliverable": "Tipo de producto inválido",
        "error.area_too_large": "El área de interés excede el tamaño máximo permitido de {max_ha} hectáreas. Por favor, suba un polígono más pequeño.",
        "error.degenerate_multipolygon_part": "{context}: El polígono nº {index} dentro del MultiPolygon es demasiado pequeño ({area} m², mínimo {threshold} m²) y probablemente sea un artefacto de digitalización. Por favor, elimine el polígono residual de su archivo GeoJSON y suba únicamente el área deseada.",
        "error.ai_empty_response": "El análisis de IA devolvió una respuesta vacía",
        "error.ai_failed": "Error al generar el análisis: {detail}",
        "error.ai_followup_empty": "La IA devolvió una respuesta vacía",
        "error.ai_followup_failed": "Error al generar la respuesta: {detail}",
        "error.ai_disabled": "El análisis con IA está desactivado actualmente.",
        "error.no_satellite_imagery": "No se encontraron imágenes de satélite para las fechas y filtros seleccionados. Intente ajustar su configuración: use fechas más antiguas, aumente el umbral de nubes o amplíe el rango de días antes/después.",
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
        language: Language code (en, pt-BR, fr, es-ES)
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
        language: Language code (en, pt-BR, fr, es-ES)
        key: Translation key (e.g., 'email.subject', 'email.body')

    Returns:
        Translated string, falls back to English if language not found.
    """
    translations = EMAIL_TRANSLATIONS.get(language, EMAIL_TRANSLATIONS["en"])
    return translations.get(key, EMAIL_TRANSLATIONS["en"].get(key, key))
