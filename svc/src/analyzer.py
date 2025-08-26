import ee
import pandas as pd
from config.settings import PRE_FIRE_DATES, POST_FIRE_DATES, SEVERITY_THRESHOLDS
from src.image_processor import get_sentinel_collection, get_best_image, calculate_differences
from src.exporter import export_local


class WildfireAnalyzer:
    """Classe para realizar análise de severidade de incêndios florestais usando dados Sentinel-2.

    Atributos:
        polygon: ee.Geometry, Região de interesse.
        pre_fire_dates: tuple, Intervalo de datas pré-fogo (início, fim).
        post_fire_dates: tuple, Intervalo de datas pós-fogo (início, fim).
        polygon_buffer: ee.Geometry, Polígono com buffer para exportações.
    """

    def __init__(self, polygon, pre_fire_dates=PRE_FIRE_DATES, post_fire_dates=POST_FIRE_DATES):
        """Inicializa o analisador com um polígono e intervalos de datas.

        Args:
            polygon: ee.Geometry, Região de interesse.
            pre_fire_dates: tuple, Intervalo de datas pré-fogo (início, fim).
            post_fire_dates: tuple, Intervalo de datas pós-fogo (início, fim).
        """
        self.polygon = polygon
        self.polygon_buffer = polygon.buffer(100)  # Buffer para exportações
        self.pre_fire_dates = pre_fire_dates
        self.post_fire_dates = post_fire_dates

    def calculate_severity(self):
        """Calcula a severidade do incêndio (ΔNBR) e retorna imagens.

        Returns:
            dict: Dicionário com imagens pré/pós-fogo, NDVI, NBR, ΔNDVI, ΔNBR, RBR e severidade.
        """
        sentinel = get_sentinel_collection(self.polygon)
        pre_fire = get_best_image(sentinel, *self.pre_fire_dates)
        post_fire = get_best_image(sentinel, *self.post_fire_dates)
        
        # Obtém NDVI, NBR, ΔNDVI, ΔNBR e RBR
        pre_ndvi, post_ndvi, pre_nbr, post_nbr, delta_ndvi, delta_nbr, rbr = calculate_differences(pre_fire, post_fire)
        
        # Classificação de severidade
        severity_expr = []
        for i, (thresh, _, val) in enumerate(SEVERITY_THRESHOLDS):
            if i == len(SEVERITY_THRESHOLDS) - 1:
                severity_expr.append(f"{val}")  # Último valor como padrão
            else:
                severity_expr.append(f"(b('DeltaNBR') < {thresh}) ? {val}")
        # Aninha as condições na ordem correta
        severity_expr = " : ".join(severity_expr)
        severity = delta_nbr.expression(severity_expr).rename('Severity')
        
        return {
            'pre_fire': pre_fire,
            'post_fire': post_fire,
            'pre_ndvi': pre_ndvi,
            'post_ndvi': post_ndvi,
            'pre_nbr': pre_nbr,
            'post_nbr': post_nbr,
            'delta_ndvi': delta_ndvi,
            'delta_nbr': delta_nbr,
            'rbr': rbr,
            'severity': severity
        }

    def calculate_area_stats(self, severity_image):
        """Calcula estatísticas de área para cada classe de severidade.

        Args:
            severity_image: ee.Image, Imagem de severidade.

        Returns:
            pd.DataFrame, Tabela com classes de severidade, áreas (ha) e porcentagens.
        """
        pixel_area = ee.Image.pixelArea().divide(10000)  # Converte para hectares
        stats_image = pixel_area.addBands(severity_image)
        stats = stats_image.reduceRegion(
            reducer=ee.Reducer.sum().group(groupField=1, groupName='Severity'),
            geometry=self.polygon,
            scale=30,
            maxPixels=1e13
        )
        
        groups = ee.List(stats.get('groups'))
        total_area = groups.map(lambda obj: ee.Dictionary(obj).get('sum')).reduce(ee.Reducer.sum())
        
        # Converte valores de severidade para strings no dicionário
        names = ee.Dictionary({str(val): name for _, name, val in SEVERITY_THRESHOLDS})
        table = groups.map(lambda obj: 
            ee.Dictionary(obj).combine({
                'SeverityName': names.get(ee.Number(ee.Dictionary(obj).get('Severity')).format('%d')),
                'Area_ha': ee.Dictionary(obj).get('sum'),
                'Percent': ee.Number(ee.Dictionary(obj).get('sum')).divide(total_area).multiply(100)
            }).select(['Severity', 'SeverityName', 'Area_ha', 'Percent'])
        )
        
        return pd.DataFrame(table.getInfo()), total_area.getInfo()

    def export_results(self, images):
        """Exporta resultados da análise para arquivos locais.

        Args:
            images: dict, Dicionário com imagens a exportar (de calculate_severity).

        Returns:
            list, Lista de caminhos dos arquivos salvos.
        """
        output_paths = [
            export_local(
                ee.FeatureCollection([ee.Feature(self.polygon)]),
                'poligono_jatai_geojson',
                self.polygon_buffer,
                output_dir='exports'
            ),
            export_local(
                images['pre_fire'].select(['B4', 'B3', 'B2']).clip(self.polygon_buffer),
                'RGB_PreFire',
                self.polygon_buffer,
                output_dir='exports'
            ),
            export_local(
                images['post_fire'].select(['B4', 'B3', 'B2']).clip(self.polygon_buffer),
                'RGB_PostFire',
                self.polygon_buffer,
                output_dir='exports'
            ),
            export_local(
                images['pre_ndvi'].clip(self.polygon_buffer),
                'NDVI_PreFire',
                self.polygon_buffer,
                output_dir='exports'
            ),
            export_local(
                images['post_ndvi'].clip(self.polygon_buffer),
                'NDVI_PostFire',
                self.polygon_buffer,
                output_dir='exports'
            ),
            export_local(
                images['pre_nbr'].clip(self.polygon_buffer),
                'NBR_PreFire',
                self.polygon_buffer,
                output_dir='exports'
            ),
            export_local(
                images['post_nbr'].clip(self.polygon_buffer),
                'NBR_PostFire',
                self.polygon_buffer,
                output_dir='exports'
            ),
            export_local(
                images['delta_nbr'].clip(self.polygon_buffer),
                'DeltaNBR',
                self.polygon_buffer,
                output_dir='exports'
            ),
            export_local(
                images['rbr'].clip(self.polygon_buffer),
                'RBR',
                self.polygon_buffer,
                output_dir='exports'
            ),
            export_local(
                images['severity'].clip(self.polygon_buffer),
                'Severity',
                self.polygon_buffer,
                output_dir='exports'
            )
        ]
        return output_paths