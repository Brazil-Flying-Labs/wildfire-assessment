"""Lógica de análise de severidade de incêndios florestais usando Google Earth Engine."""
import logging
import os
import shutil
from typing import Dict, List, Optional, Tuple

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

logger = logging.getLogger(__name__)


class WildfireAnalyzer:
    """
    Forest fire severity analyzer using Sentinel-2 data.

    Generates 9 types of processed images + area statistics.
    """

    # Constant Settings
    BRIGHTNESS_FACTOR = 1.8
    BUFFER_METERS = 5000
    OVERLAY_WIDTH = 3
    S3_BUCKET = 'wildfire-assessment-dev'
    
    # Color palettes for visualization
    RBR_PALETTE = ['black', 'yellow', 'red']
    SEVERITY_PALETTE = ['00FF00', 'FFFF00', 'FFA500', 'FF0000', '8B4513']
    RBR_THRESHOLDS = [0.035, 0.130, 0.298]

    def __init__(self, polygon: ee.Geometry, pre_fire_dates: Tuple[str, str], 
                 post_fire_dates: Tuple[str, str], polygon_id: str, execution_id: str):
        """
        Initializes the analyzer.
        
        Args:
            polygon: Geometry of the region of interest
            pre_fire_dates: Pre-fire dates (start, end)
            post_fire_dates: Post-fire dates (start, end) 
            polygon_id: Polygon/reserve ID
            execution_id: Unique execution ID
        """
        self.polygon = polygon
        self.polygon_id = polygon_id
        self.execution_id = execution_id
        self.pre_fire_dates = pre_fire_dates
        self.post_fire_dates = post_fire_dates
        
        self.folder = f"{execution_id}/{polygon_id}"
        self.export_region = polygon.bounds()
        self.center_point = polygon.centroid()
        
        self._log_geometry_info()

    def _log_geometry_info(self):
        """Logs geometry information for debugging."""
        logger.debug("Polygon coordinates: %s", self.polygon.coordinates().getInfo())
        logger.debug("Export region: %s", self.export_region.coordinates().getInfo())
        
        bounds = self.export_region.bounds().coordinates().getInfo()[0]
        lon_min, lat_min = bounds[0]
        lon_max, lat_max = bounds[2]
        
        width_m = (lon_max - lon_min) * 111320
        height_m = (lat_max - lat_min) * 111320
        scale = 10
        
        logger.debug("Dimensões: %s x %s pixels (escala: %sm)",
                    f"{width_m/scale:.0f}", f"{height_m/scale:.0f}", scale)
    
    def _classify_severity(self, delta_nbr: ee.Image) -> ee.Image:
        """Classifies severity based on ΔNBR."""
        severity_expr = []
        for i, (thresh, _, val) in enumerate(SEVERITY_THRESHOLDS):
            if i == len(SEVERITY_THRESHOLDS) - 1:
                severity_expr.append(f"{val}")
            else:
                severity_expr.append(f"(b('DeltaNBR') < {thresh}) ? {val}")
        
        return delta_nbr.expression(" : ".join(severity_expr)).rename('Severity')

    def _classify_rbr_severity(self, rbr: ee.Image) -> ee.Image:
        """Classifies severity based on RBR."""
        rbr_severity_expr = []
        for i, thresh in enumerate(self.RBR_THRESHOLDS):
            rbr_severity_expr.append(f"(b('RBR') < {thresh}) ? {i}")
        rbr_severity_expr.append("3")
        
        return rbr.expression(" : ".join(rbr_severity_expr)).rename('RBR_Severity')

    def calculate_severity(self) -> Dict[str, ee.Image]:
        """Calculates fire severity and returns processed images."""
        sentinel = get_sentinel_collection(self.polygon)
        
        # Returns the best pre-fire and post-fire images 
        pre_fire_image, pre_date = get_best_image(sentinel, *self.pre_fire_dates, self.polygon)
        post_fire_image, post_date = get_best_image(sentinel, *self.post_fire_dates, self.polygon)
        
        logger.debug("Pre-fire coverage: %s", pre_fire_image.geometry().bounds().getInfo())
        logger.debug("Post-fire coverage: %s", post_fire_image.geometry().bounds().getInfo())
        
        # Calculates differences between images
        pre_ndvi, post_ndvi, pre_nbr, post_nbr, delta_ndvi, delta_nbr, rbr = calculate_differences(pre_fire_image, post_fire_image)
        
        # Classifies severities
        severity = self._classify_severity(delta_nbr)
        rbr_classified = self._classify_rbr_severity(rbr)
        
        return {
            'pre_fire': pre_fire_image,
            'post_fire': post_fire_image,
            'pre_ndvi': pre_ndvi,
            'post_ndvi': post_ndvi,
            'pre_nbr': pre_nbr,
            'post_nbr': post_nbr,
            'delta_ndvi': delta_ndvi,
            'delta_nbr': delta_nbr,
            'rbr': rbr,
            'severity': severity,
            'rbr_classified': rbr_classified,
            'pre_fire_best_date': pre_date,
            'post_fire_best_date': post_date
        }

    def calculate_area_stats(self, severity_image: ee.Image) -> Tuple[pd.DataFrame, float]:
        """Calculates area statistics by severity class."""
        pixel_area = ee.Image.pixelArea().divide(10000)  # Converts to hectares
        stats_image = pixel_area.addBands(severity_image)
        
        stats = stats_image.reduceRegion(
            reducer=ee.Reducer.sum().group(groupField=1, groupName='Severity'),
            geometry=self.polygon,
            scale=30,
            maxPixels=1e13
        )
        
        groups = ee.List(stats.get('groups'))
        total_area = groups.map(lambda obj: ee.Dictionary(obj).get('sum')).reduce(ee.Reducer.sum())
        
        # Processes statistics
        severity_stats = self._process_severity_stats(groups.getInfo())
        self._export_stats_to_csv(severity_stats)
        
        return severity_stats, total_area.getInfo()

    def _process_severity_stats(self, groups: List) -> pd.DataFrame:
        """Processes groups of statistics into a DataFrame."""
        severity_palette = ['green', 'yellow', 'orange', 'red', 'maroon']
        severity_colors = {str(val): color for (_, _, val), color in zip(SEVERITY_THRESHOLDS, severity_palette)}
        names = {str(val): name for _, name, val in SEVERITY_THRESHOLDS}
        
        table_data = []
        total_sum = sum(g.get('sum', 0) for g in groups if g.get('sum'))
        
        for obj in groups:
            severity_val = str(obj.get('Severity'))
            area_ha = obj.get('sum')
            percent = (area_ha / total_sum * 100) if area_ha and total_sum else 0
            
            table_data.append({
                'Severity': severity_val,
                'SeverityName': names.get(severity_val, ''),
                'Area_ha': area_ha,
                'Percent': percent,
                'Color': severity_colors.get(severity_val, 'unknown')
            })
        
        return pd.DataFrame(table_data)
    
    def _export_stats_to_csv(self, stats_df: pd.DataFrame):
        """Exports statistics to CSV and uploads to S3."""
        export_dir = f'exports/{self.folder}'
        os.makedirs(export_dir, exist_ok=True)
        
        csv_path = f'{export_dir}/severity_stats.csv'
        stats_df.to_csv(csv_path, index=False)
        
        self._upload_to_s3(csv_path, f'wildfire/{self.folder}/severity_stats.csv')
    
    def _upload_to_s3(self, local_path: str, s3_key: str):
        """Uploads file to S3."""
        try:
            session = get_boto3_session()
            s3 = session.client('s3')
            s3.upload_file(local_path, self.S3_BUCKET, s3_key)
            logger.info("File uploaded: %s → s3://%s/%s", local_path, self.S3_BUCKET, s3_key)
        except NoCredentialsError:
            logger.error("AWS credentials not configured properly.")
        except Exception as e:
            logger.exception("Error uploading to S3: %s", str(e))

    def _prepare_rgb_images(self, pre_fire: ee.Image, post_fire: ee.Image) -> Tuple[ee.Image, ee.Image]:
        """Prepares RGB images with brightness adjustment."""
        def create_rgb_image(image):
            return ee.Image.cat([
                image.select('B4').divide(10000).multiply(255).uint8(),
                image.select('B3').divide(10000).multiply(255).uint8(),
                image.select('B2').divide(10000).multiply(255).uint8()
            ]).rename(['R', 'G', 'B'])
        
        rgb_pre = create_rgb_image(pre_fire)
        rgb_post = create_rgb_image(post_fire)
        
        # Applies brightness adjustment
        if self.BRIGHTNESS_FACTOR != 1.0:
            rgb_pre = rgb_pre.toFloat().multiply(self.BRIGHTNESS_FACTOR).clamp(0, 255).uint8()
            rgb_post = rgb_post.toFloat().multiply(self.BRIGHTNESS_FACTOR).clamp(0, 255).uint8()
        
        return rgb_pre, rgb_post
    
    def _create_polygon_overlay(self) -> ee.Image:
        """Creates polygon overlay for images."""
        return ee.Image().paint(self.polygon, 1, self.OVERLAY_WIDTH).visualize(
            palette=['purple'], opacity=0.7
        )
    
    def _export_image(self, image: ee.Image, name: str, extension: str) -> Optional[str]:
        """Exports an individual image."""
        region = self.polygon.buffer(self.BUFFER_METERS).bounds(1)
        export_dir = f'exports/{self.folder}'
        
        try:
            path = export_local(image, name, region, extension, output_dir=export_dir)
            if path and os.path.exists(path) and os.path.getsize(path) > 0:
                logger.debug("File exported: %s (%s bytes)", path, os.path.getsize(path))
                return path
            else:
                logger.warning("Failed to export %s.%s", name, extension)
                return None
        except Exception as e:
            logger.exception("Error exporting %s.%s: %s", name, extension, e)
            return None
        
    def export_results(self, images: Dict[str, ee.Image], export_full_image: bool = False) -> List[Dict]:
        """Exports all analysis results."""
        # Prepare basic components
        rbr_rgb = images['rbr'].visualize(min=-0.5, max=0.6, palette=self.RBR_PALETTE)
        rgb_pre, rgb_post = self._prepare_rgb_images(images['pre_fire'], images['post_fire'])
        poly_overlay = self._create_polygon_overlay()
        
        # Define all exports
        export_configs = [
            # RBR images
            (images['rbr'].visualize(min=0, max=1).blend(poly_overlay), 'RBR_Pure', 'tif'),
            (rbr_rgb.blend(poly_overlay), 'RBR_Color', 'tif'),
            (rbr_rgb.blend(poly_overlay), 'RBR_Color', 'jpg'),
            
            # Severity images
            (images['rbr_classified'].visualize(min=0, max=4, palette=self.SEVERITY_PALETTE).blend(poly_overlay), 
             'Severity_RBR_Color', 'tif'),
            (images['rbr_classified'].visualize(min=0, max=4, palette=self.SEVERITY_PALETTE).blend(poly_overlay), 
             'Severity_RBR_Color', 'jpg'),
            
            # RGB images
            (rgb_pre.visualize(min=0, max=255).blend(poly_overlay), 'RGB_PreFire', 'tif'),
            (rgb_pre.visualize(min=0, max=255).blend(poly_overlay), 'RGB_PreFire', 'jpg'),
            (rgb_post.visualize(min=0, max=255).blend(poly_overlay), 'RGB_PostFire', 'tif'),
            (rgb_post.visualize(min=0, max=255).blend(poly_overlay), 'RGB_PostFire', 'jpg'),
        ]
        
        # Execute exports
        output_paths = []
        for image, name, ext in export_configs:
            if path := self._export_image(image, name, ext):
                output_paths.append(path)
        
        # Additional exports if requested
        if export_full_image:
            output_paths.extend(self._export_full_images(images, poly_overlay))
        
        # Process uploads and cleanup
        presigned_urls = self._process_uploads(output_paths)
        self._cleanup_export_dir()
        
        return presigned_urls
    
    def _export_full_images(self, images: Dict[str, ee.Image], poly_overlay: ee.Image) -> List[str]:
        """Exports full images (full image)."""
        rgb_pre_full, rgb_post_full = self._prepare_rgb_images(images['pre_fire'], images['post_fire'])
        poly_mask = ee.Image().paint(self.polygon, 1, self.OVERLAY_WIDTH)
        poly_mask_vis = poly_mask.visualize(palette=['blue'], min=1, max=1)
        
        paths = []
        
        pre_full_vis = rgb_pre_full.visualize(min=0, max=255).blend(poly_mask_vis)
        if path := self._export_image(pre_full_vis, 'PreFire_Full', 'tif'):
            paths.append(path)
            
        post_full_vis = rgb_post_full.visualize(min=0, max=255).blend(poly_mask_vis)
        if path := self._export_image(post_full_vis, 'PostFire_Full', 'tif'):
            paths.append(path)
            
        return paths

    def _process_uploads(self, output_paths: List[str]) -> List[Dict]:
        """Processes uploads to S3 and generates presigned URLs."""
        presigned_urls = []
        s3_prefix = f'wildfire/{self.folder}/'
        
        for path in output_paths:
            if not path or not os.path.exists(path):
                continue
                
            filename = os.path.basename(path)
            s3_key = f"{s3_prefix}{filename}"
            
            self._upload_to_s3(path, s3_key)
            presigned_url = generate_presigned_url(self.S3_BUCKET, s3_key, expiration=3600)
            presigned_urls.append({"key": s3_key, "url": presigned_url})
            logger.info("URL generated for: %s", s3_key)
        
        # Upload statistics CSV
        csv_path = f'exports/{self.folder}/severity_stats.csv'
        if os.path.exists(csv_path):
            s3_key = f"{s3_prefix}severity_stats.csv"
            self._upload_to_s3(csv_path, s3_key)
            presigned_url = generate_presigned_url(self.S3_BUCKET, s3_key, expiration=3600)
            presigned_urls.append({"key": s3_key, "url": presigned_url})
        
        return presigned_urls
    
    def _cleanup_export_dir(self):
        """Cleans up local export directory."""
        export_dir = f'exports/{self.folder}'
        try:
            if os.path.exists(export_dir) and os.path.isdir(export_dir):
                if os.listdir(export_dir):
                    shutil.rmtree(export_dir)
                    logger.info("Directory removed: %s", export_dir)
                else:
                    os.rmdir(export_dir)
                    logger.info("Empty directory removed: %s", export_dir)
        except Exception as e:
            logger.exception("Error cleaning %s: %s", export_dir, e)