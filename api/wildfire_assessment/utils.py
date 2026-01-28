import json
import smtplib
from datetime import datetime, timedelta
from email.message import EmailMessage

import ee


def load_polygon(file_name):
    """Carrega todos os polígonos de arquivos GeoJSON em um diretório.

    Args:
        directory_path: str, Caminho para o diretório contendo arquivos GeoJSON.

    Returns:
        list, Lista de tuplas (nome do arquivo, ee.Geometry) correspondentes aos polígonos carregados.
    """

    file_path = "../../polygons/" + file_name

    with open(file_path, "r", encoding="utf-8") as f:
        geojson = json.load(f)

    # Se o GeoJSON tiver múltiplas features, use FeatureCollection e pegue a geometria agregada
    try:
        features = geojson.get("features")
        if features and len(features) > 1:
            fc = ee.FeatureCollection(features)
            geometry = fc.geometry()
        else:
            geometry = ee.Geometry(features[0]["geometry"]) if features else ee.Geometry(geojson)
    except Exception:
        # Fallback genérico
        geometry = ee.Geometry(geojson)

    return geometry


def calculate_date_range(date, days_before=60, days_after=60):
    """
    Calculates a date range around a given date.

    Args:
        date (datetime.date or datetime.datetime): The reference date.
        days_before (int): Number of days before the reference date.
        days_after (int): Number of days after the reference date.

    Returns:
        tuple: (date_before, date_after) as datetime objects, or (None, None) if input is invalid.
    """
    if not date:
        return None, None
    try:
        date_before = date - timedelta(days=days_before)
        date_after = date + timedelta(days=days_after)
        return date_before, date_after
    except (ValueError, TypeError):
        return None, None


def send_gmail_email(username: str, password: str, to_address: str, subject: str, body: str) -> None:
    """Send a simple plain-text email using Gmail's SMTP servers.

    Gmail requires either OAuth or an app password when 2FA is enabled. For local
    development use an app password. The function raises smtplib.SMTPException on
    failures so callers can handle retries/logging as needed.
    """

    message = EmailMessage()
    message["From"] = username
    message["To"] = to_address
    message["Subject"] = subject
    message.set_content(body)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(username, password)
            smtp.send_message(message)
    except smtplib.SMTPAuthenticationError as exc:  # pragma: no cover - network call
        raise RuntimeError(
            "Gmail rejected the credentials. Generate a Mail app password after enabling 2-Step Verification "
            "and update the backend secrets (see README.md#gmail-smtp-setup)."
        ) from exc
