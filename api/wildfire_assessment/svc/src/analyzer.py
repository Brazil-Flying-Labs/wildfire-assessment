"""Lógica de análise de severidade de incêndios florestais usando Google Earth Engine."""
import os

import ee
import pandas as pd
from botocore.exceptions import NoCredentialsError
from wildfire_assessment.svc.config.settings import SEVERITY_THRESHOLDS
from wildfire_assessment.svc.src.aws import generate_presigned_url, get_boto3_session
from wildfire_assessment.svc.src.exporter import export_local
from wildfire_assessment.svc.src.image_processor import (
    calculate_differences,
    get_best_image,
    get_sentinel_collection,
)


class WildfireAnalyzer:
    """Classe para realizar análise de severidade de incêndios florestais usando dados Sentinel-2.

    Atributos:
        polygon: ee.Geometry, Região de interesse.
        pre_fire_dates: tuple, Intervalo de datas pré-fogo (início, fim).
        post_fire_dates: tuple, Intervalo de datas pós-fogo (início, fim).
        export_region: ee.Geometry, Região de exportação baseada no polígono.
        filename: str or int, Nome do arquivo GeoJSON ou ID da reserva ecológica.
    """

    def __init__(self, polygon, pre_fire_dates, post_fire_dates, filename):
        """Inicializa o analisador com um polígono e intervalos de datas.

        Args:
            polygon: ee.Geometry, Região de interesse.
            filename: str or int, Nome do arquivo GeoJSON ou ID da reserva ecológica.
            pre_fire_dates: tuple, Intervalo de datas pré-fogo (início, fim).
            post_fire_dates: tuple, Intervalo de datas pós-fogo (início, fim).
        """
        self.polygon = polygon
        self.filename = filename or "poligono"
        self.pre_fire_dates = pre_fire_dates
        self.post_fire_dates = post_fire_dates
        self.center_point = polygon.centroid()
        # Usar o envelope do polígono com buffer de 1000 metros
        self.export_region = polygon.buffer(1000).bounds()
        print(f"Coordenadas do polígono original: {self.polygon.coordinates().getInfo()}")
        print(f"Coordenadas da região de exportação: {self.export_region.coordinates().getInfo()}")
        # Verificar dimensões aproximadas da grade de pixels
        bounds = self.export_region.bounds().coordinates().getInfo()[0]
        lon_min, lat_min = bounds[0]
        lon_max, lat_max = bounds[2]
        # Aproximar distância em metros (assumindo projeção aproximada)
        width_m = (lon_max - lon_min) * 111320  # 1 grau ≈ 111.32 km na longitude
        height_m = (lat_max - lat_min) * 111320  # 1 grau ≈ 111.32 km na latitude
        scale = 10  # Escala ajustada para 10 metros (nativa Sentinel-2)
        print(f"Dimensões aproximadas: {width_m/scale:.0f} x {height_m/scale:.0f} pixels (escala: {scale}m)")

    def calculate_severity(self):
        """Calcula a severidade do incêndio (ΔNBR) e retorna imagens.

        Returns:
            dict: Dicionário com imagens pré/pós-fogo, NDVI, NBR, ΔNDVI, ΔNBR, RBR e severidade.
        """
        sentinel = get_sentinel_collection(self.polygon)
        pre_fire = get_best_image(sentinel, *self.pre_fire_dates, self.polygon)  # Passe polygon
        post_fire = get_best_image(sentinel, *self.post_fire_dates, self.polygon)  # Passe polygon
        
        # Clip explícito para garantir recorte
        pre_fire = pre_fire.clip(self.polygon)
        post_fire = post_fire.clip(self.polygon)
        
        # Verifique cobertura
        print(f"Cobertura pre_fire: {pre_fire.geometry().bounds().getInfo()}")
        print(f"Cobertura post_fire: {post_fire.geometry().bounds().getInfo()}")
        
        # Obtém NDVI, NBR, ΔNDVI, ΔNBR e RBR
        pre_ndvi, post_ndvi, pre_nbr, post_nbr, delta_ndvi, delta_nbr, rbr = calculate_differences(pre_fire, post_fire)
        
        # Classificação de severidade (existente, para ΔNBR) — inalterado
        severity_expr = []
        for i, (thresh, _, val) in enumerate(SEVERITY_THRESHOLDS):
            if i == len(SEVERITY_THRESHOLDS) - 1:
                severity_expr.append(f"{val}")  # Último valor como padrão
            else:
                severity_expr.append(f"(b('DeltaNBR') < {thresh}) ? {val}")
        severity_expr = " : ".join(severity_expr)
        severity = delta_nbr.expression(severity_expr).rename('Severity')
        
        # Corrigido: Classificação para RBR, com thresholds ajustados (assumindo não escalado; ajuste se necessário)
        rbr_thresholds = [0.035, 0.130, 0.298]  # Boundaries para unchanged/low, low/mod, mod/high
        rbr_severity_expr = []
        for i, thresh in enumerate(rbr_thresholds):
            rbr_severity_expr.append(f"(b('RBR') < {thresh}) ? {i}")
        rbr_severity_expr.append("3")  # Valor final para alta severidade (ou mais classes se precisar)
        rbr_severity_expr = " : ".join(rbr_severity_expr)
        rbr_classified = rbr.expression(rbr_severity_expr).rename('RBR_Severity')
        
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
            'severity': severity,
            'rbr_classified': rbr_classified  # Novo: RBR classificado
        }
    def calculate_area_stats(self, severity_image):
        """Calcula estatísticas de área para cada classe de severidade e exporta para CSV localmente.

        Args:
            severity_image: ee.Image, Imagem de severidade.

        Returns:
            pd.DataFrame, Tabela com classes de severidade, áreas (ha) e porcentagens.
        """
        prefix = str(self.filename).replace('.geojson', '') if isinstance(self.filename, str) else f"{self.filename}"
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
        names = ee.Dictionary({str(val): name for _, name, val in SEVERITY_THRESHOLDS})
        table = groups.map(lambda obj:
            ee.Dictionary(obj).combine({
                'SeverityName': names.get(ee.Number(ee.Dictionary(obj).get('Severity')).format('%d')),
                'Area_ha': ee.Dictionary(obj).get('sum'),
                'Percent': ee.Number(ee.Dictionary(obj).get('sum')).divide(total_area).multiply(100)
            }).select(['Severity', 'SeverityName', 'Area_ha', 'Percent'])
        )
        df = pd.DataFrame(table.getInfo())
        export_dir = f'exports/{prefix}'
        os.makedirs(export_dir, exist_ok=True)  # Cria o diretório se não existir
        csv_local_path = f'{export_dir}/{self.filename}_severity_stats.csv'
        df.to_csv(csv_local_path, index=False)

        # Upload do CSV para S3
        session = get_boto3_session()
        s3 = session.client('s3')
        bucket_name = 'wildfire-assessment-dev'  # Substitua pelo nome do seu bucket S3
        s3_key = f'wildfire/{prefix}/{self.filename}_severity_stats.csv'
        try:
            s3.upload_file(csv_local_path, bucket_name, s3_key)
            print(f"Arquivo CSV {csv_local_path} enviado para s3://{bucket_name}/{s3_key}")
        except NoCredentialsError:
            print("Credenciais da AWS não encontradas. Configure suas credenciais.")
        except Exception as e:
            print(f"Erro ao enviar {csv_local_path} para S3: {str(e)}")

        return df, total_area.getInfo()
    def export_results(self, images):
        """Exporta resultados da análise para arquivos locais.

        Args:
            images: dict, Dicionário com imagens a exportar (de calculate_severity).

        Returns:
            list, Lista de caminhos dos arquivos salvos.
        """
        # Usar o nome do arquivo GeoJSON ou ID como prefixo e subpasta
        prefix = str(self.filename).replace('.geojson', '') if isinstance(self.filename, str) else f"{self.filename}"
        # Paleta de cores para RBR (valores de -1 a 1, azul para baixo, vermelho para alto)
        rbr_palette = ['green', 'yellow', 'orange', 'red', 'maroon']
        rbr_rgb = images['rbr_classified'].clip(self.polygon).visualize(
            min=0,
            max=len(rbr_palette) - 1,
            palette=rbr_palette
        )
        # Verificar bandas disponíveis
        print(f"Bandas disponíveis para pre_fire: {images['pre_fire'].bandNames().getInfo()}")
        print(f"Bandas disponíveis para post_fire: {images['post_fire'].bandNames().getInfo()}")
        # Combinar bandas RGB explicitamente
        rgb_pre = ee.Image.cat([
            images['pre_fire'].select('B4').divide(10000).multiply(255).uint8(),
            images['pre_fire'].select('B3').divide(10000).multiply(255).uint8(),
            images['pre_fire'].select('B2').divide(10000).multiply(255).uint8()
        ]).rename(['R', 'G', 'B']).clip(self.polygon)  # Clip
        rgb_post = ee.Image.cat([
            images['post_fire'].select('B4').divide(10000).multiply(255).uint8(),
            images['post_fire'].select('B3').divide(10000).multiply(255).uint8(),
            images['post_fire'].select('B2').divide(10000).multiply(255).uint8()
        ]).rename(['R', 'G', 'B']).clip(self.polygon)  # Clip
        print(f"Bandas selecionadas para RGB_PreFire: {rgb_pre.bandNames().getInfo()}")
        print(f"Bandas selecionadas para RGB_PostFire: {rgb_post.bandNames().getInfo()}")
        
        # Clip nas outras imagens antes de exportar
        for key in ['pre_ndvi', 'post_ndvi', 'pre_nbr', 'post_nbr', 'delta_ndvi', 'delta_nbr', 'severity']:
            images[key] = images[key].clip(self.polygon)
        
        output_paths = [
            export_local(
                ee.FeatureCollection([ee.Feature(self.polygon)]),
                f'{prefix}_poligono_geojson',
                self.export_region,
                'geojson',
                output_dir=f'exports/{prefix}'
            ),
            export_local(
                rbr_rgb,
                f'{prefix}_RBR',
                self.polygon,
                'tif',
                output_dir=f'exports/{prefix}'
            ),
            export_local(
                images['severity'],
                f'{prefix}_Severity',
                self.polygon,
                'tif',
                output_dir=f'exports/{prefix}'
            ),
            export_local(
                rbr_rgb,
                f'{prefix}_RBR_Severity',
                self.polygon,
                'png',
                output_dir=f'exports/{prefix}'
            ),
            
            # Opcional: Se quiser também exportar o RBR classificado numérico (sem cor, para análise)
            export_local(
                images['rbr_classified'],
                f'{prefix}_RBR_Classified',
                self.polygon,
                'tif',
                output_dir=f'exports/{prefix}'
            )
        ]

        session = get_boto3_session()
        s3 = session.client('s3')
        bucket_name = 'wildfire-assessment-dev'  # Substitua pelo nome do seu bucket S3
        s3_prefix = f'wildfire/{prefix}/'

        presigned_urls = []

        def upload_to_s3(local_path, s3_key):
            try:
                s3.upload_file(local_path, bucket_name, s3_key)
                print(f"Arquivo {local_path} enviado para s3://{bucket_name}/{s3_key}")
            except NoCredentialsError:
                print("Credenciais da AWS não encontradas. Configure suas credenciais.")
            except Exception as e:
                print(f"Erro ao enviar {local_path} para S3: {str(e)}")
    
        for path in output_paths:
            if path.endswith(('.tif', '.geojson', 'png', 'csv')):  # Filtra apenas arquivos de imagem ou geojson
                s3_key = f"{s3_prefix}{path.split('/')[-1]}"
                upload_to_s3(path, s3_key)
                presigned_url = generate_presigned_url(bucket_name, s3_key, expiration=3600)
                presigned_urls.append({"key": s3_key, "url": presigned_url})
                print(f"Pre-signed URL gerado para {s3_key}: {presigned_url}")
        
        csv_local_path = f'exports/{prefix}/{self.filename}_severity_stats.csv'
        if os.path.exists(csv_local_path):
            s3_key = f"{s3_prefix}{self.filename}_severity_stats.csv"
            upload_to_s3(csv_local_path, s3_key)
            presigned_url = generate_presigned_url(bucket_name, s3_key, expiration=3600)
            presigned_urls.append({"key": s3_key, "url": presigned_url})
            print(f"Pre-signed URL gerado para {s3_key}: {presigned_url}")

        
        return presigned_urls