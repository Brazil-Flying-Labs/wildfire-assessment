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
    # Planejamento das nove imagens finais para entrega
    # 1. RBR puro (1 banda, TIFF georreferenciado)
    # 2. RBR colorido com polígono (TIFF georreferenciado)
    # 3. RBR colorido com polígono (JPEG não georreferenciado)
    # 4. Severity RBR colorido com polígono (TIFF georreferenciado)
    # 5. Severity RBR colorido com polígono (JPEG não georreferenciado)
    # 6. RGB pré fogo com polígono (TIFF georreferenciado)
    # 7. RGB pré fogo com polígono (JPEG não georreferenciado)
    # 8. RGB pós fogo com polígono (TIFF georreferenciado)
    # 9. RGB pós fogo com polígono (JPEG não georreferenciado)
    # Para cada imagem, definir: imagem base, formato, overlay, georreferenciamento
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
        self.export_region = polygon.bounds()
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
        pre_fire, date = get_best_image(sentinel, *self.pre_fire_dates, self.polygon)  # Passe polygon
        post_fire, date = get_best_image(sentinel, *self.post_fire_dates, self.polygon)  # Passe polygon
        

        
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
            pd.DataFrame, Tabela com classes de severidade, áreas (ha), porcentagens e cores.
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
        
        # Definir paleta de cores (mesma usada em export_results para consistência)
        severity_palette = ['green', 'yellow', 'orange', 'red', 'maroon']
        # Mapear valores de severidade para cores usando SEVERITY_THRESHOLDS
        severity_colors = {str(val): color for (_, _, val), color in zip(SEVERITY_THRESHOLDS, severity_palette)}
        names = {str(val): name for _, name, val in SEVERITY_THRESHOLDS}
        print("Groups:", groups.getInfo())

        # Converter grupos para lista de dicionários Python
        table_py = []
        for obj in groups.getInfo():
            severity_val = str(obj.get('Severity'))
            color_name = severity_colors.get(severity_val, 'unknown')
            name = names.get(severity_val, '')
            area_ha = obj.get('sum')
            percent = (area_ha / sum([g.get('sum') for g in groups.getInfo()])) * 100 if area_ha is not None else 0
            table_py.append({
                'Severity': severity_val,
                'SeverityName': name,
                'Area_ha': area_ha,
                'Percent': percent,
                'Color': color_name
            })
        df = pd.DataFrame(table_py)
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

    def export_results(self, images, export_full_image=False):
        """Exporta resultados da análise para arquivos locais.

        Args:
            images: dict, Dicionário com imagens a exportar (de calculate_severity).
            export_full_image: bool, Se True exporta a imagem Sentinel-2 sem corte por polígono.

        Returns:
            list, Lista de caminhos dos arquivos salvos.
        """
        prefix = str(self.filename).replace('.geojson', '') if isinstance(self.filename, str) else f"{self.filename}"
        rbr_palette = ['green', 'yellow', 'orange', 'red', 'maroon']
        rbr_rgb = images['rbr_classified'].visualize(
            min=0,
            max=len(rbr_palette) - 1,
            palette=rbr_palette
        )
        print(f"Bandas disponíveis para pre_fire: {images['pre_fire'].bandNames().getInfo()}")
        print(f"Bandas disponíveis para post_fire: {images['post_fire'].bandNames().getInfo()}")
        rgb_pre = ee.Image.cat([
            images['pre_fire'].select('B4').divide(10000).multiply(255).uint8(),
            images['pre_fire'].select('B3').divide(10000).multiply(255).uint8(),
            images['pre_fire'].select('B2').divide(10000).multiply(255).uint8()
        ]).rename(['R', 'G', 'B'])
        rgb_post = ee.Image.cat([
            images['post_fire'].select('B4').divide(10000).multiply(255).uint8(),
            images['post_fire'].select('B3').divide(10000).multiply(255).uint8(),
            images['post_fire'].select('B2').divide(10000).multiply(255).uint8()
        ]).rename(['R', 'G', 'B'])
        print(f"Bandas selecionadas para RGB_PreFire: {rgb_pre.bandNames().getInfo()}")
        print(f"Bandas selecionadas para RGB_PostFire: {rgb_post.bandNames().getInfo()}")

        for key in ['pre_ndvi', 'post_ndvi', 'pre_nbr', 'post_nbr', 'delta_ndvi', 'delta_nbr', 'severity']:
            images[key] = images[key]

        # Usa buffer do polígono para exportar área de interesse sem exceder limites
        buffer_m = 5000
        region_buffer = self.polygon.buffer(buffer_m).bounds(1)
        # Overlay do polígono em roxo
        poly_overlay = ee.Image().paint(self.polygon, 1, 1).visualize(palette=['purple'], opacity=0.7)

        # 1. RBR puro (TIFF georreferenciado, 1 banda) + overlay
        rbr_pure_vis = images['rbr'].visualize(min=0, max=1).blend(poly_overlay)
        output_paths = [
            export_local(
                rbr_pure_vis,
                f'{prefix}_RBR_Pure',
                region_buffer,
                'tif',
                output_dir=f'exports/{prefix}'
            ),
        ]
        # 2. RBR colorido com polígono (TIFF georreferenciado) + overlay
        rbr_color_vis = rbr_rgb.blend(poly_overlay)
        output_paths.append(
            export_local(
                rbr_color_vis,
                f'{prefix}_RBR_Color',
                region_buffer,
                'tif',
                output_dir=f'exports/{prefix}'
            )
        )
        # 3. RBR colorido com polígono (JPEG não georreferenciado) + overlay
        output_paths.append(
            export_local(
                rbr_color_vis,
                f'{prefix}_RBR_Color',
                region_buffer,
                'jpg',
                output_dir=f'exports/{prefix}'
            )
        )
        # 4. Severity RBR colorido com polígono (TIFF georreferenciado) + overlay
        severity_rgb = images['rbr_classified'].visualize(
            min=0,
            max=len(rbr_palette) - 1,
            palette=rbr_palette
        ).blend(poly_overlay)
        output_paths.append(
            export_local(
                severity_rgb,
                f'{prefix}_Severity_RBR_Color',
                region_buffer,
                'tif',
                output_dir=f'exports/{prefix}'
            )
        )
        # 5. Severity RBR colorido com polígono (JPEG não georreferenciado) + overlay
        output_paths.append(
            export_local(
                severity_rgb,
                f'{prefix}_Severity_RBR_Color',
                region_buffer,
                'jpg',
                output_dir=f'exports/{prefix}'
            )
        )
        # 6. RGB pré fogo com polígono (TIFF georreferenciado) + overlay
        rgb_pre_vis = rgb_pre.visualize(min=0, max=255).blend(poly_overlay)
        output_paths.append(
            export_local(
                rgb_pre_vis,
                f'{prefix}_RGB_PreFire',
                region_buffer,
                'tif',
                output_dir=f'exports/{prefix}'
            )
        )
        # 7. RGB pré fogo com polígono (JPEG não georreferenciado) + overlay
        output_paths.append(
            export_local(
                rgb_pre_vis,
                f'{prefix}_RGB_PreFire',
                region_buffer,
                'jpg',
                output_dir=f'exports/{prefix}'
            )
        )
        # 8. RGB pós fogo com polígono (TIFF georreferenciado) + overlay
        rgb_post_vis = rgb_post.visualize(min=0, max=255).blend(poly_overlay)
        output_paths.append(
            export_local(
                rgb_post_vis,
                f'{prefix}_RGB_PostFire',
                region_buffer,
                'tif',
                output_dir=f'exports/{prefix}'
            )
        )
        # 9. RGB pós fogo com polígono (JPEG não georreferenciado) + overlay
        output_paths.append(
            export_local(
                rgb_post_vis,
                f'{prefix}_RGB_PostFire',
                region_buffer,
                'jpg',
                output_dir=f'exports/{prefix}'
            )
        )

        if export_full_image:
            # Visualização RGB do tile completo
            rgb_pre_full = ee.Image.cat([
                images['pre_fire'].select('B4').divide(10000).multiply(255).uint8(),
                images['pre_fire'].select('B3').divide(10000).multiply(255).uint8(),
                images['pre_fire'].select('B2').divide(10000).multiply(255).uint8()
            ]).rename(['R', 'G', 'B'])
            rgb_post_full = ee.Image.cat([
                images['post_fire'].select('B4').divide(10000).multiply(255).uint8(),
                images['post_fire'].select('B3').divide(10000).multiply(255).uint8(),
                images['post_fire'].select('B2').divide(10000).multiply(255).uint8()
            ]).rename(['R', 'G', 'B'])

            # Desenhar polígono sobre o tile
            poly_mask = ee.Image().paint(self.polygon, 1, 3)  # 3px de largura
            poly_mask_vis = poly_mask.visualize(palette=['blue'], min=1, max=1)
            rgb_pre_full_vis = rgb_pre_full.visualize(min=0, max=255).blend(poly_mask_vis)
            rgb_post_full_vis = rgb_post_full.visualize(min=0, max=255).blend(poly_mask_vis)

            output_paths.append(
                export_local(
                    rgb_pre_full_vis,
                    f'{prefix}_PreFire_Full',
                    region_buffer,
                    'tif',
                    output_dir=f'exports/{prefix}'
                )
            )
            output_paths.append(
                export_local(
                    rgb_post_full_vis,
                    f'{prefix}_PostFire_Full',
                    region_buffer,
                    'tif',
                    output_dir=f'exports/{prefix}'
                )
            )

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
            if path.endswith(('.tif', '.geojson', '.png', '.jpg', '.jpeg', '.csv')):  # Inclui .jpg/.jpeg/.png
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