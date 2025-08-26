import os
from dotenv import load_dotenv

import ee
import json
import os
from src.auth import initialize_gee
from src.analyzer import WildfireAnalyzer
from config.settings import POLYGON_PATH

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# def save_image_from_request(request, timestamp, prefix, band) -> str:
#     """
#     Uploads the image data from a SentinelHubRequest to an S3 bucket.

#     Args:
#         request (SentinelHubRequest): The request object containing the image data.
#         timestamp (datetime): The timestamp for naming the saved image file.
#         prefix (str): The prefix to use for the S3 object key.

#     Returns:
#         str: The S3 URI of the uploaded image.
#     """
    
#     file_name = f"{band}.tiff"
#     folder_name = f"s2-l2a-cdse_{timestamp.strftime('%Y-%m-%d_%H-%M-%S')}"
#     # breakpoint()
#     image = Image.fromarray(np.float32(request.get_data()[0]))
#     buffer = io.BytesIO()
#     image.save(buffer, format="TIFF")
#     buffer.seek(0)

#     session = get_boto3_session()


#     if os.getenv("ENV") != "local":
#         logger.info("Uploading image to S3...")
#         session = get_boto3_session()

#         s3 = session.client("s3")

#         bucket_name = os.getenv("S3_BUCKET_NAME")

#         s3.upload_fileobj(buffer, bucket_name, f"{prefix}/{folder_name}/{file_name}")

#         return f"s3://{bucket_name}/{prefix}/{file_name}"
#     else:
#         logger.info("Saving image locally...")
#         local_path = os.path.join(".", prefix, folder_name, file_name)
#         os.makedirs(os.path.dirname(local_path), exist_ok=True)
#         image.save(local_path)
#         return local_path

"""Script principal para análise de severidade de incêndios florestais."""

def load_polygon(file_path):
    """Carrega o polígono de um arquivo GeoJSON.

    Args:
        file_path: str, Caminho para o arquivo GeoJSON.

    Returns:
        ee.Geometry, Polígono carregado.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            geojson = json.load(f)
        return ee.Geometry(geojson['features'][0]['geometry'])
    except Exception as e:
        print(f"Erro ao carregar o polígono: {e}")
        raise

def main():
    """Função principal para executar a análise de severidade."""
    try:
        # Inicializar GEE
        initialize_gee()

        # Carregar polígono
        polygon = load_polygon(POLYGON_PATH)

        # Criar e executar análise
        analyzer = WildfireAnalyzer(polygon)
        images = analyzer.calculate_severity()
        
        # Calcular estatísticas de área
        stats_df, total_area = analyzer.calculate_area_stats(images['severity'])
        print("Resumo de Severidade (ΔNBR - área e %):")
        print(stats_df)
        print(f"Área total do polígono (geométrica, ha): {total_area}")

        # Exportar resultados localmente
        print("Iniciando exportações locais. Aguarde...")
        output_paths = analyzer.export_results(images)
        print("Exportações concluídas! Arquivos salvos em:")
        for path in output_paths:
            print(f"- {path}")

    except Exception as e:
        print(f"Erro durante a análise: {e}")
        raise

if __name__ == "__main__":
    main()