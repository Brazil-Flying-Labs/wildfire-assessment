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
                    print(f"Aviso: Nenhum polígono encontrado em {file_path}")
                    continue
                # Carregar a primeira feature do GeoJSON
                geometry = ee.Geometry(geojson['features'][0]['geometry'])
                geometries.append((file_path.name, geometry))
                print(f"Polígono carregado de {file_path}")
            except Exception as e:
                print(f"Erro ao carregar o polígono de {file_path}: {e}")
                continue  # Continuar com o próximo arquivo em caso de erro

        if not geometries:
            raise ValueError("Nenhum polígono válido foi carregado dos arquivos GeoJSON")
        return geometries

    except Exception as e:
        print(f"Erro ao varrer o diretório {directory_path}: {e}")
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
            print(f"\nProcessando polígono: {filename}")
            # Criar e executar análise, passando o nome do arquivo
            analyzer = WildfireAnalyzer(polygon, filename=filename, pre_fire_dates=PRE_FIRE_DATES, post_fire_dates=POST_FIRE_DATES)
            images = analyzer.calculate_severity()
            
            # Calcular estatísticas de área
            stats_df, total_area = analyzer.calculate_area_stats(images['severity'])
            print(f"Resumo de Severidade (ΔNBR - área e %) para {filename}:")
            print(stats_df)
            print(f"Área total do polígono (geométrica, ha): {total_area}")

            # Exportar resultados localmente
            print(f"Iniciando exportações locais para {filename}. Aguarde...")
            output_paths = analyzer.export_results(images)
            print(f"Exportações concluídas para {filename}! Arquivos salvos em:")
            for path in output_paths:
                print(f"- {path}")

    except Exception as e:
        print(f"Erro durante a análise: {e}")
        raise

if __name__ == "__main__":
    main()