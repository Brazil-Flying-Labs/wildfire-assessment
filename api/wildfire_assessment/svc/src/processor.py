import ast
import csv
import io
import json
import logging
import os
import time
import uuid

from dotenv import load_dotenv
from wildfire_analyser import Deliverable, FireSeverity, PostFireAssessment
from wildfire_assessment.svc.src.aws import get_aws_secret_manager_secret, upload_to_s3

logger = logging.getLogger(__name__)
load_dotenv()

def process_fire_assessment(
        fire_id: int, execution_id: uuid.UUID, pre_fire_date: str, post_fire_date: str, polygon_path: str
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
            GEE_PRIVATE_KEY_JSON = GEE_PRIVATE_KEY_JSON.replace('\\"', '"').replace('\\\\', '\\')
    # Executa a análise


    runner = PostFireAssessment(
        GEE_PRIVATE_KEY_JSON,
        polygon_path, 
        pre_fire_date, 
        post_fire_date, 
        deliverables=[
            Deliverable.RGB_PRE_FIRE,
            Deliverable.RGB_POST_FIRE,
            Deliverable.NDVI_PRE_FIRE,
            Deliverable.NDVI_POST_FIRE,
            Deliverable.RBR,
        ])
    
    result = runner.run_analysis()

    # Processa os dados de severidade
    area_by_severity_data = get_severity_data(result["area_by_severity"])
    
    # Log das informações de severidade
    logger.info("Dados de severidade processados:")
    for row in area_by_severity_data:
        logger.info(
            f"{row['severity_name']}({row['severity']}): {row['ha']:.2f} ha ({row['percent']:.2f}%) -> {row['color']}"
        )

    # Configuração do caminho S3
    bucket_name = 'wildfire-assessment-dev'
    s3_prefix = f"wildfire/{execution_id}/{fire_id}"
    
    # Upload das imagens para o S3
    s3_urls = {}
    
    for filename, file_info in result["images"].items():
        s3_key = f"{s3_prefix}/{filename}"
        
        try:
            # Faz upload do arquivo para o S3
            s3_object_url, presigned_url = upload_to_s3(
                data=file_info["data"],
                bucket_name=bucket_name,
                s3_key=s3_key,
                content_type=file_info["content_type"]
            )
            
            s3_urls[filename] = {
                "s3_url": s3_object_url,
                "presigned_url": presigned_url,
                "content_type": file_info["content_type"],
                "s3_key": s3_key
            }
            
        except Exception as e:
            logger.error(f"Erro ao fazer upload de {filename} para S3: {e}")
            continue

    # Gera e salva o CSV com area_by_severity
    try:
        csv_data = generate_severity_csv(area_by_severity_data)
        csv_key = f"{s3_prefix}/area_by_severity.csv"
        
        s3_object_url, presigned_url = upload_to_s3(
            data=csv_data,
            bucket_name=bucket_name,
            s3_key=csv_key,
            content_type="text/csv"
        )
        
        s3_urls["area_by_severity.csv"] = {
            "s3_url": s3_object_url,
            "presigned_url": presigned_url,
            "content_type": "text/csv",
            "s3_key": csv_key
        }
        
    except Exception as e:
        logger.error(f"Erro ao gerar CSV de severidade: {e}")

    # Salva as métricas como JSON no S3
    metrics_data = {
        "area_by_severity": area_by_severity_data,
        "timings": result["timings"],
        "fire_id": fire_id,
        "execution_id": str(execution_id),
        "pre_fire_date": pre_fire_date,
        "post_fire_date": post_fire_date,
        "processed_at": time.strftime('%Y-%m-%dT%H:%M:%SZ')
    }
    
    try:
        metrics_json = json.dumps(metrics_data, indent=2).encode('utf-8')
        metrics_key = f"{s3_prefix}/metrics.json"
        
        s3_object_url, presigned_url = upload_to_s3(
            data=metrics_json,
            bucket_name=bucket_name,
            s3_key=metrics_key,
            content_type="application/json"
        )
        
        s3_urls["metrics.json"] = {
            "s3_url": s3_object_url,
            "presigned_url": presigned_url,
            "content_type": "application/json",
            "s3_key": metrics_key
        }
        
    except Exception as e:
        logger.error(f"Erro ao salvar métricas no S3: {e}")

    return {
        "s3_urls": s3_urls,
        "analysis_results": {
            "area_by_severity": area_by_severity_data,
            "timings": result["timings"]
        },
        "s3_base_path": f"s3://{bucket_name}/{s3_prefix}"
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
        4: "#8B4513"   # Very High - marrom
    }
    
    # Se for uma lista (novo formato)
    if isinstance(area_by_severity, list):
        for item in area_by_severity:
            # Se cada item já for um dicionário com as chaves esperadas
            if isinstance(item, dict):
                severity_data.append({
                    'severity': item.get('severity', 0),
                    'severity_name': item.get('severity_name', 'Unknown'),
                    'ha': item.get('ha', 0.0),
                    'percent': item.get('percent', 0.0),
                    'color': item.get('color', color_map.get(item.get('severity', 0), "#000000"))
                })
    
    # Se for um dicionário (formato antigo)
    elif isinstance(area_by_severity, dict):
        total_area = sum(area_by_severity.values())
        
        for severity, area in area_by_severity.items():
            severity_enum = FireSeverity(int(severity))
            percent = (area / total_area * 100) if total_area > 0 else 0
            
            severity_data.append({
                'severity': int(severity),
                'severity_name': severity_enum.label,
                'ha': float(area),
                'percent': float(percent),
                'color': color_map.get(int(severity), "#000000")
            })
    
    # Ordena por severidade
    severity_data.sort(key=lambda x: x['severity'])
    
    return severity_data

def generate_severity_csv(severity_data: list) -> bytes:
    """
    Gera um CSV com os dados completos de área por severidade
    """
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Escreve o cabeçalho
    writer.writerow(["severity_class", "severity_name", "area_hectares", "percent", "color"])
    
    # Escreve os dados
    for row in severity_data:
        writer.writerow([
            row['severity'],
            row['severity_name'],
            f"{row['ha']:.2f}",
            f"{row['percent']:.2f}",
            row['color']
        ])
    
    return output.getvalue().encode('utf-8')

def deliverable_to_filename(assessment_result):
    """
    Mapeia um Deliverable para um nome de arquivo padrão
    """
    presigned_data = {}
    
    for _, file_info in assessment_result["s3_urls"].items():
        s3_key = file_info.get("s3_key", "")
        
        if s3_key.endswith("rbr.tif"):
            presigned_data["rbr_pure_tif"] = file_info["presigned_url"]
        elif s3_key.endswith("severity_visual.jpg"):
            presigned_data["severity_visual_jpg"] = file_info["presigned_url"]
        elif s3_key.endswith("rbr_visual.jpg"):
            presigned_data["rbr_visual_jpg"] = file_info["presigned_url"]
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