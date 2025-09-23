import json
import logging
import os
from pathlib import Path

import ee
from config.settings import POLYGON_PATH
from dotenv import load_dotenv
from src.analyzer import WildfireAnalyzer
from src.auth import initialize_gee

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_polygon(directory_path):
    """Carrega todos os polígonos de arquivos GeoJSON em um diretório.

    Args:
        directory_path: str, Caminho para o diretório contendo arquivos GeoJSON.

    Returns:
        list, Lista de tuplas (nome do arquivo, ee.Geometry) correspondentes aos polígonos carregados.
    """
    try:
        # Converter o caminho para Path e verificar se é um diretório
        directory = Path(directory_path)
        if not directory.is_dir():
            raise ValueError(f"O caminho fornecido não é um diretório: {directory_path}")

        # Buscar todos os arquivos .geojson no diretório
        geojson_files = list(directory.glob("*.geojson"))
        if not geojson_files:
            raise FileNotFoundError(f"Nenhum arquivo GeoJSON encontrado em {directory_path}")

        geometries = []
        for file_path in geojson_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    geojson = json.load(f)
                # Verificar se o arquivo GeoJSON contém features
                if 'features' not in geojson or not geojson['features']:
                    logger.warning("Nenhum polígono encontrado em %s", file_path)
                    continue
                # Se houver múltiplas features no GeoJSON, agrega como FeatureCollection
                try:
                    features = geojson.get('features')
                    if features and len(features) > 1:
                        fc = ee.FeatureCollection(features)
                        geometry = fc.geometry()
                    else:
                        geometry = ee.Geometry(features[0]['geometry']) if features else ee.Geometry(geojson)
                except Exception as e:
                    logger.warning("Erro ao processar geometria como FeatureCollection: %s. Tentando abordagem genérica.", e)
                    geometry = ee.Geometry(geojson)
                geometries.append((file_path.name, geometry))
                logger.info("Polígono carregado de %s", file_path)
            except Exception as e:
                logger.exception("Erro ao carregar o polígono de %s: %s", file_path, e)
                continue  # Continuar com o próximo arquivo em caso de erro

        if not geometries:
            raise ValueError("Nenhum polígono válido foi carregado dos arquivos GeoJSON")
        return geometries

    except Exception as e:
        logger.exception("Erro ao varrer o diretório %s: %s", directory_path, e)
        raise

def main():
    """Função principal para executar a análise de severidade."""
    try:
        # Inicializar GEE
        initialize_gee()

        # Carregar polígonos do diretório
        PRE_FIRE_DATES = ('2024-06-01', '2024-10-01')
        POST_FIRE_DATES = ('2024-10-17', '2024-12-31')
        polygon_list = load_polygon(POLYGON_PATH)

        # Processar cada polígono
        for filename, polygon in polygon_list:
            logger.info("Processando polígono: %s", filename)
            # Criar e executar análise, passando o nome do arquivo
            analyzer = WildfireAnalyzer(polygon, filename=filename, pre_fire_dates=PRE_FIRE_DATES, post_fire_dates=POST_FIRE_DATES)
            images = analyzer.calculate_severity()
            
            # Calcular estatísticas de área
            stats_df, total_area = analyzer.calculate_area_stats(images['severity'])
            logger.info("Resumo de Severidade (ΔNBR - área e %) para %s:", filename)
            logger.info("%s", stats_df)
            logger.info("Área total do polígono (geométrica, ha): %s", total_area)

            # Exportar resultados localmente
            logger.info("Iniciando exportações locais para %s. Aguarde...", filename)
            output_paths = analyzer.export_results(images)
            logger.info("Exportações concluídas para %s! Arquivos salvos em:", filename)
            for path in output_paths:
                logger.info("- %s", path)

    except Exception as e:
        logger.exception("Erro durante a análise: %s", e)
        raise

if __name__ == "__main__":
    main()