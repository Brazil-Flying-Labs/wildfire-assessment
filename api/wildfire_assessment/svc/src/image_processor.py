import logging
from datetime import datetime, timezone
from typing import Optional, Tuple

import ee

logger = logging.getLogger(__name__)


class SentinelProcessor:
    """Sentinel-2 image processor for wildfire analysis."""
    
    # Settings
    CLOUD_COVER_THRESHOLD = 20
    COLLECTION_ID = "COPERNICUS/S2_SR_HARMONIZED"
    
    @classmethod
    def get_sentinel_collection(cls, polygon: ee.Geometry) -> ee.ImageCollection:
        """
        Gets the Sentinel-2 image collection filtered for the region.
        
        Args:
            polygon: Geometry of the region of interest
            
        Returns:
            Filtered Sentinel-2 image collection
        """
        collection = (
            ee.ImageCollection(cls.COLLECTION_ID)
            .filterBounds(polygon)
            .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", cls.CLOUD_COVER_THRESHOLD))
        )
        return collection

    @classmethod
    def get_best_image(
        cls, 
        collection: ee.ImageCollection, 
        start_date: str, 
        end_date: str, 
        polygon: Optional[ee.Geometry] = None
    ) -> Tuple[ee.Image, str]:
        """
        Finds the best image (least clouds) in the date range.
        
        Args:
            collection: Sentinel-2 image collection
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            polygon: Polygon for additional filtering (optional)
            
        Returns:
            Tuple with (mosaic_image, image_date)
            
        Raises:
            ValueError: If no valid image is found
        """
        cls._log_date_range(start_date, end_date)
        
        # Filter by date and cloud cover
        filtered = cls._filter_collection(collection, start_date, end_date)
        
        # Create mosaic with the best image
        best_image = cls._create_best_image_mosaic(filtered)
        
        # Get image date
        image_date = cls._extract_image_date(filtered)
        
        return best_image, image_date

    @classmethod
    def _log_date_range(cls, start_date: str, end_date: str):
        """Logs information about the date range."""
        logger.debug("=" * 50)
        logger.debug("Data inicial: %s", start_date)
        logger.debug("Data final: %s", end_date)

    @classmethod
    def _filter_collection(
        cls, 
        collection: ee.ImageCollection, 
        start_date: str, 
        end_date: str
    ) -> ee.ImageCollection:
        """Filter collection by date and cloud cover."""
        filtered = (
            collection
            .filterDate(start_date, end_date)
            .filterMetadata("CLOUDY_PIXEL_PERCENTAGE", "less_than", cls.CLOUD_COVER_THRESHOLD)
        )
        
        image_count = filtered.size().getInfo()
        logger.debug("Imagens após filtragem: %s", image_count)
        logger.debug("=" * 50)
        
        return filtered

    @classmethod
    def _create_best_image_mosaic(cls, collection: ee.ImageCollection) -> ee.Image:
        """Creates a mosaic with the image of the least cloud cover."""
        image_count = collection.size().getInfo()
        
        if image_count == 0:
            raise ValueError("No valid image found for the provided dates and region.")
        
        return collection.sort("CLOUDY_PIXEL_PERCENTAGE").mosaic()

    @classmethod
    def _extract_image_date(cls, collection: ee.ImageCollection) -> str:
        """Extracts the date of the first image (least clouds) in the collection."""
        first_image = collection.sort("CLOUDY_PIXEL_PERCENTAGE").first()
        
        if not first_image:
            raise ValueError("Could not get image from collection.")
        
        timestamp = first_image.get("system:time_start").getInfo()
        
        if not timestamp:
            raise ValueError("Could not get image timestamp.")
        
        logger.debug("Timestamp obtained: %s", timestamp)
        return cls._timestamp_to_date(timestamp)

    @classmethod
    def _timestamp_to_date(cls, timestamp: int) -> str:
        """Converts timestamp in milliseconds to date string."""
        return datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc).strftime("%Y-%m-%d")

    @classmethod
    def calculate_vegetation_indices(
        cls, 
        pre_fire: ee.Image, 
        post_fire: ee.Image
    ) -> Tuple[ee.Image, ee.Image, ee.Image, ee.Image, ee.Image, ee.Image, ee.Image]:
        """
        Calculates vegetation indices and differences for wildfire analysis.
        
        Args:
            pre_fire: pre-fire image
            post_fire: post-fire image
            
        Returns:
            Tuple with:
            - pre_ndvi, post_ndvi: pre and post-fire NDVI
            - pre_nbr, post_nbr: pre and post-fire NBR 
            - delta_ndvi, delta_nbr: Differences of the indices
            - rbr: Relative Burn Ratio
        """
        # Calculation of NDVI (Normalized Difference Vegetation Index)
        pre_ndvi, post_ndvi = cls._calculate_ndvi(pre_fire, post_fire)
        
        # Calculation of NBR (Normalized Burn Ratio)
        pre_nbr, post_nbr = cls._calculate_nbr(pre_fire, post_fire)
        
        # Differences between periods
        delta_ndvi = cls._calculate_difference(pre_ndvi, post_ndvi, "DeltaNDVI")
        delta_nbr = cls._calculate_difference(pre_nbr, post_nbr, "DeltaNBR")
        
        # RBR (Relative Burn Ratio)
        rbr = cls._calculate_rbr(pre_nbr, post_nbr)
        
        return pre_ndvi, post_ndvi, pre_nbr, post_nbr, delta_ndvi, delta_nbr, rbr

    @classmethod
    def _calculate_ndvi(cls, pre_fire: ee.Image, post_fire: ee.Image) -> Tuple[ee.Image, ee.Image]:
        """Calculates NDVI for pre and post-fire images."""
        pre_ndvi = pre_fire.normalizedDifference(["B8", "B4"]).rename("NDVI")
        post_ndvi = post_fire.normalizedDifference(["B8", "B4"]).rename("NDVI")
        return pre_ndvi, post_ndvi

    @classmethod
    def _calculate_nbr(cls, pre_fire: ee.Image, post_fire: ee.Image) -> Tuple[ee.Image, ee.Image]:
        """Calculates NBR for pre and post-fire images."""
        pre_nbr = pre_fire.normalizedDifference(["B8", "B12"]).rename("NBR")
        post_nbr = post_fire.normalizedDifference(["B8", "B12"]).rename("NBR")
        return pre_nbr, post_nbr

    @classmethod
    def _calculate_difference(cls, pre_index: ee.Image, post_index: ee.Image, name: str) -> ee.Image:
        """Calculates difference between pre and post-fire indices."""
        return pre_index.subtract(post_index).rename(name)

    @classmethod
    def _calculate_rbr(cls, pre_nbr: ee.Image, post_nbr: ee.Image) -> ee.Image:
        """Calculates Relative Burn Ratio (RBR)."""
        # RBR = (preNBR - postNBR) / (preNBR + 1.001)
        # The 1.001 prevents division by zero
        numerator = pre_nbr.subtract(post_nbr)
        denominator = pre_nbr.add(1.001)
        return numerator.divide(denominator).rename("RBR")


# Compatibility functions (maintains original interface)
def get_sentinel_collection(polygon):
    """Gets Sentinel-2 collection filtered for the region."""
    return SentinelProcessor.get_sentinel_collection(polygon)


def get_best_image(collection, start_date, end_date, polygon=None):
    """Gets the best image in the date range."""
    return SentinelProcessor.get_best_image(collection, start_date, end_date, polygon)


def calculate_differences(pre_fire, post_fire):
    """Calculates vegetation indices and differences."""
    return SentinelProcessor.calculate_vegetation_indices(pre_fire, post_fire)