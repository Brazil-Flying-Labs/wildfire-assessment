import csv
import io
import json
import logging
import os
import time
import uuid

import ee
from celery import shared_task
from dotenv import load_dotenv
from wildfire_analyser.fire_assessment.auth import authenticate_gee
from wildfire_analyser.fire_assessment.deliverables import Deliverable
from wildfire_analyser.fire_assessment.post_fire_assessment import PostFireAssessment
from wildfire_assessment.svc.src.aws import get_aws_secret_manager_secret, upload_to_s3
from wildfire_assessment.utils import send_gmail_email

logger = logging.getLogger(__name__)
load_dotenv()


def process_fire_assessment(
    fire_id: int,
    execution_id: uuid.UUID,
    pre_fire_date: str,
    post_fire_date: str,
    polygon_path: str,
) -> dict:
    """
    Processa a avaliação de incêndio e salva os resultados diretamente no S3
    Retorna um dicionário com pre-signed URLs para acesso temporário
    """
    # Check the environment
    ENV = os.environ.get("ENV", "local")

    secret = json.loads(get_aws_secret_manager_secret(ENV))
    GEE_PRIVATE_KEY_JSON = secret["GEE_PRIVATE_KEY_JSON"]

    if isinstance(GEE_PRIVATE_KEY_JSON, str):
        if GEE_PRIVATE_KEY_JSON.startswith("'") and GEE_PRIVATE_KEY_JSON.endswith("'"):
            GEE_PRIVATE_KEY_JSON = GEE_PRIVATE_KEY_JSON[1:-1]
        GEE_PRIVATE_KEY_JSON = GEE_PRIVATE_KEY_JSON.replace('\\"', '"').replace(
            "\\\\", "\\"
        )
    # Executa a análise

    runner = PostFireAssessment(
        GEE_PRIVATE_KEY_JSON,
        polygon_path,
        pre_fire_date,
        post_fire_date,
        deliverables=[
            Deliverable.RGB_PRE_FIRE_VISUAL,
            Deliverable.RGB_POST_FIRE_VISUAL,
            Deliverable.DNDVI_VISUAL,
            Deliverable.DNBR_VISUAL,
            Deliverable.RBR_VISUAL,
            Deliverable.DNBR_AREA_STATISTICS,
        ],
    )

    result = runner.run()
    area_statistics = json.dumps(result["statistics"]["DNBR_AREA_STATISTICS"])
    # Processa os dados de severidade
    area_by_severity_raw = (
        result.get("area_by_severity")
        or result.get("analysis_results", {}).get("area_by_severity")
        or []
    )
    if not area_by_severity_raw:
        logger.warning("Resultado sem 'area_by_severity'.")

    area_by_severity_data = get_severity_data(area_by_severity_raw)

    # Log das informações de severidade
    logger.info("Dados de severidade processados:")
    for row in area_by_severity_data:
        logger.info(
            f"{row['severity_name']}({row['severity']}): {row['ha']:.2f} ha ({row['percent']:.2f}%) -> {row['color']}"
        )

    # Configuração do caminho S3
    bucket_name = "wildfire-assessment-dev"
    s3_prefix = f"wildfire/{execution_id}/{fire_id}"

    # Usa URLs já fornecidas quando disponíveis; caso contrário faz upload para o S3
    s3_urls = {}
    uses_visual_urls = bool(result.get("visual")) and isinstance(
        result.get("visual"), dict
    )

    def _guess_content_type(filename: str) -> str:
        lowered = filename.lower()
        if lowered.endswith(".jpg") or lowered.endswith(".jpeg"):
            return "image/jpeg"
        if lowered.endswith(".tif") or lowered.endswith(".tiff"):
            return "image/tiff"
        return "application/octet-stream"

    if uses_visual_urls:
        for filename, item in result["visual"].items():
            url = item.get("url") if isinstance(item, dict) else item
            if not url:
                continue
            s3_urls[filename] = {
                "s3_url": url,
                "presigned_url": url,
                "content_type": _guess_content_type(filename),
                "s3_key": filename,
            }
    elif "images" in result and isinstance(result.get("images"), dict):
        for filename, file_info in result["images"].items():
            s3_key = f"{s3_prefix}/{filename}"

            try:
                # Faz upload do arquivo para o S3
                s3_object_url, presigned_url = upload_to_s3(
                    data=file_info["data"],
                    bucket_name=bucket_name,
                    s3_key=s3_key,
                    content_type=file_info["content_type"],
                )

                s3_urls[filename] = {
                    "s3_url": s3_object_url,
                    "presigned_url": presigned_url,
                    "content_type": file_info["content_type"],
                    "s3_key": s3_key,
                }

            except Exception as e:
                logger.error(f"Erro ao fazer upload de {filename} para S3: {e}")
                continue

    # Gera e salva o CSV com area_by_severity
    if area_by_severity_data and not uses_visual_urls:
        try:
            csv_data = generate_severity_csv(area_by_severity_data)
            csv_key = f"{s3_prefix}/area_by_severity.csv"

            s3_object_url, presigned_url = upload_to_s3(
                data=csv_data,
                bucket_name=bucket_name,
                s3_key=csv_key,
                content_type="text/csv",
            )

            s3_urls["area_by_severity.csv"] = {
                "s3_url": s3_object_url,
                "presigned_url": presigned_url,
                "content_type": "text/csv",
                "s3_key": csv_key,
            }

        except Exception as e:
            logger.error(f"Erro ao gerar CSV de severidade: {e}")

    # Salva as métricas como JSON no S3
    metrics_data = {
        "area_by_severity": area_by_severity_data,
        "timings": result.get("timings", {}),
        "fire_id": fire_id,
        "execution_id": str(execution_id),
        "pre_fire_date": pre_fire_date,
        "post_fire_date": post_fire_date,
        "processed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    if not uses_visual_urls:
        try:
            metrics_json = json.dumps(metrics_data, indent=2).encode("utf-8")
            metrics_key = f"{s3_prefix}/metrics.json"

            s3_object_url, presigned_url = upload_to_s3(
                data=metrics_json,
                bucket_name=bucket_name,
                s3_key=metrics_key,
                content_type="application/json",
            )

            s3_urls["metrics.json"] = {
                "s3_url": s3_object_url,
                "presigned_url": presigned_url,
                "content_type": "application/json",
                "s3_key": metrics_key,
            }

        except Exception as e:
            logger.error(f"Erro ao salvar métricas no S3: {e}")

    return {
        "s3_urls": s3_urls,
        "analysis_results": {
            "area_by_severity": area_by_severity_data,
            "timings": result.get("timings", {}),
        },
        "s3_base_path": None if uses_visual_urls else f"s3://{bucket_name}/{s3_prefix}",
        "area_statistics": area_statistics,
    }


def get_severity_data(area_by_severity):
    """
    Processa os dados de severidade independentemente do formato.
    Retorna uma lista padronizada de dicionários.
    """
    severity_data = []

    # Mapeamento de cores padrão
    color_map = {
        0: "#00FF00",  # Unburned - verde
        1: "#FFFF00",  # Low - amarelo
        2: "#FFA500",  # Moderate - laranja
        3: "#FF0000",  # High - vermelho
        4: "#8B4513",  # Very High - marrom
    }

    severity_label_map = {
        0: "Unburned",
        1: "Low",
        2: "Moderate",
        3: "High",
        4: "Very High",
    }

    # Se for uma lista (novo formato)
    if isinstance(area_by_severity, list):
        for item in area_by_severity:
            # Se cada item já for um dicionário com as chaves esperadas
            if isinstance(item, dict):
                severity_data.append(
                    {
                        "severity": item.get("severity", 0),
                        "severity_name": item.get("severity_name", "Unknown"),
                        "ha": item.get("ha", 0.0),
                        "percent": item.get("percent", 0.0),
                        "color": item.get(
                            "color", color_map.get(item.get("severity", 0), "#000000")
                        ),
                    }
                )

    # Se for um dicionário (formato antigo)
    elif isinstance(area_by_severity, dict):
        total_area = sum(area_by_severity.values())

        for severity, area in area_by_severity.items():
            severity_value = int(severity)
            percent = (area / total_area * 100) if total_area > 0 else 0

            severity_data.append(
                {
                    "severity": severity_value,
                    "severity_name": severity_label_map.get(severity_value, "Unknown"),
                    "ha": float(area),
                    "percent": float(percent),
                    "color": color_map.get(severity_value, "#000000"),
                }
            )

    # Ordena por severidade
    severity_data.sort(key=lambda x: x["severity"])

    return severity_data


def generate_severity_csv(severity_data: list) -> bytes:
    """
    Gera um CSV com os dados completos de área por severidade
    """
    output = io.StringIO()
    writer = csv.writer(output)

    # Escreve o cabeçalho
    writer.writerow(
        ["severity_class", "severity_name", "area_hectares", "percent", "color"]
    )

    # Escreve os dados
    for row in severity_data:
        writer.writerow(
            [
                row["severity"],
                row["severity_name"],
                f"{row['ha']:.2f}",
                f"{row['percent']:.2f}",
                row["color"],
            ]
        )

    return output.getvalue().encode("utf-8")


def deliverable_to_filename(assessment_result):
    """
    Mapeia um Deliverable para um nome de arquivo padrão
    """
    presigned_data = {}

    deliverable_name_map = {
        "rgb_pre_fire_visual": "rgb_pre_fire_visual_jpg",
        "rgb_post_fire_visual": "rgb_post_fire_visual_jpg",
        "dndvi_visual": "dndvi_visual_jpg",
        "dnbr_visual": "dnbr_visual_jpg",
        "rbr_visual": "rbr_visual_jpg",
        "severity_visual": "severity_visual_jpg",
    }

    for _, file_info in assessment_result["s3_urls"].items():
        s3_key = file_info.get("s3_key", "")

        normalized_key = s3_key.split("/")[-1]
        normalized_key_no_ext = normalized_key.rsplit(".", 1)[0].lower()

        if normalized_key_no_ext in deliverable_name_map:
            presigned_data[deliverable_name_map[normalized_key_no_ext]] = file_info[
                "presigned_url"
            ]
        elif s3_key.endswith("rbr.tif"):
            presigned_data["rbr_pure_tif"] = file_info["presigned_url"]
        elif s3_key.endswith("severity_visual.jpg"):
            presigned_data["severity_visual_jpg"] = file_info["presigned_url"]
        elif s3_key.endswith("rbr_visual.jpg"):
            presigned_data["rbr_visual_jpg"] = file_info["presigned_url"]
        elif s3_key.endswith("dndvi_visual.jpg"):
            presigned_data["dndvi_visual_jpg"] = file_info["presigned_url"]
        elif s3_key.endswith("dnbr_visual.jpg"):
            presigned_data["dnbr_visual_jpg"] = file_info["presigned_url"]
        elif s3_key.endswith("rgb_pre_fire.tif"):
            presigned_data["rgb_pre_fire_tif"] = file_info["presigned_url"]
        elif s3_key.endswith("rgb_post_fire.tif"):
            presigned_data["rgb_post_fire_tif"] = file_info["presigned_url"]
        elif s3_key.endswith("rgb_pre_fire_visual.jpg"):
            presigned_data["rgb_pre_fire_visual_jpg"] = file_info["presigned_url"]
        elif s3_key.endswith("rgb_post_fire_visual.jpg"):
            presigned_data["rgb_post_fire_visual_jpg"] = file_info["presigned_url"]
        elif s3_key.endswith("ndvi_pre_fire.tif"):
            presigned_data["ndvi_pre_fire_tif"] = file_info["presigned_url"]
        elif s3_key.endswith("ndvi_post_fire.tif"):
            presigned_data["ndvi_post_fire_tif"] = file_info["presigned_url"]
        elif s3_key.endswith("area_by_severity.csv"):
            presigned_data["severity_stats"] = file_info["presigned_url"]

    return presigned_data


@shared_task
def process_scientific_deliverable(
    *,
    pre_fire_date: str,
    post_fire_date: str,
    polygon_path: str,
    deliverable_name: str,
    email: str,
    reserve_name: str,
) -> str:
    """Kick off a single scientific deliverable export in the background."""
    try:
        deliverable = Deliverable[deliverable_name]
    except KeyError as exc:
        raise ValueError(f"Invalid deliverable '{deliverable_name}'") from exc

    POLL_INTERVAL_SECONDS = 15

    def wait_for_task(gee_task_id: str):
        while True:
            statuses = ee.data.getTaskStatus(gee_task_id)

            if not statuses:
                raise RuntimeError(f"Task {gee_task_id} not found")

            status = statuses[0]
            state = status["state"]

            print(f"[GEE] task={gee_task_id} state={state}")

            if state == "COMPLETED":
                return state

            if state in ("FAILED", "CANCELLED"):
                error = status.get("error_message", "Unknown error")
                raise RuntimeError(f"Task failed: {error}")

            time.sleep(POLL_INTERVAL_SECONDS)

    # Check the environment
    ENV = os.environ.get("ENV", "local")

    polygon_path = f"../../polygons/{polygon_path}"

    secret = json.loads(get_aws_secret_manager_secret(ENV))
    GEE_PRIVATE_KEY_JSON = secret["GEE_PRIVATE_KEY_JSON"]

    if isinstance(GEE_PRIVATE_KEY_JSON, str):
        if GEE_PRIVATE_KEY_JSON.startswith("'") and GEE_PRIVATE_KEY_JSON.endswith("'"):
            GEE_PRIVATE_KEY_JSON = GEE_PRIVATE_KEY_JSON[1:-1]
        GEE_PRIVATE_KEY_JSON = GEE_PRIVATE_KEY_JSON.replace('\\"', '"').replace(
            "\\\\", "\\"
        )

    # Executa a análise para o deliverable específico
    runner = PostFireAssessment(
        GEE_PRIVATE_KEY_JSON,
        polygon_path,
        pre_fire_date,
        post_fire_date,
        deliverables=[deliverable],
        gcs_bucket="wildfire-analyser-outputs",
        verbose=False,
    )

    result = runner.run()

    authenticate_gee(gee_key_json=GEE_PRIVATE_KEY_JSON)

    if deliverable == Deliverable.RGB_PRE_FIRE:
        deliverable_key = "RGB_PRE_FIRE"
    elif deliverable == Deliverable.RGB_POST_FIRE:
        deliverable_key = "RGB_POST_FIRE"
    elif deliverable == Deliverable.DNBR:
        deliverable_key = "DNBR"
    elif deliverable == Deliverable.RBR:
        deliverable_key = "RBR"
    elif deliverable == Deliverable.DNDVI:
        deliverable_key = "DNDVI"
    else:
        raise ValueError("Invalid deliverable type")

    result_wait = wait_for_task(result["scientific"][deliverable_key]["gee_task_id"])

    if result_wait == "COMPLETED":
        send_gmail_email(
            username="Brazil@flyinglabs.org",
            password=secret["GMAIL_PWD"],
            to_address=email,
            subject="Wildfire Analyser - Scientific Deliverable Ready",
            body=(
                f"The scientific deliverable '{reserve_name}' is ready for download on"
                f" this link: {result['scientific'][deliverable_key]['url']}"
            ),
        )
    return result_wait
