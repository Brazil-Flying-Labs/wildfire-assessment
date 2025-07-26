import rasterio
#import numpy as np
import matplotlib.pyplot as plt

# Função para ler banda Sentinel-2
def read_band(filepath):
    with rasterio.open(filepath) as src:
        return src.read(1).astype(float), src.profile

# Caminhos para as bandas (exemplo)
band4_path = 'b4.tiff'  # Vermelho
band8_path = 'b8.tiff'  # NIR
band12_path = 'b12.tiff' # SWIR

# Leitura das bandas, todas com mesmo profile, 
# swir reamostrado pelo copernicus browser
red, profile = read_band(band4_path)
nir, _ = read_band(band8_path)
swir, _ = read_band(band12_path)

# Calcular NDVI
ndvi = (nir - red) / (nir + red + 1e-10)

# Calcular NBR
nbr = (nir - swir) / (nir + swir + 1e-10)

# Salvar NDVI como GeoTIFF
profile.update(dtype=rasterio.float32, count=1)
with rasterio.open('ndvi.tif', 'w', **profile) as dst:
    dst.write(ndvi.astype(rasterio.float32), 1)
print("NDVI salvo como ndvi.tif")

# Salvar NBR como GeoTIFF
with rasterio.open('nbr.tif', 'w', **profile) as dst:
    dst.write(nbr.astype(rasterio.float32), 1)
print("NBR salvo como nbr.tif")

# Visualizar NDVI
plt.figure(figsize=(12,5))
plt.subplot(1,2,1)
plt.imshow(ndvi, cmap='RdYlGn', vmin=-1, vmax=1)
plt.colorbar()
plt.title('NDVI Sentinel-2')

# Visualizar NBR
plt.subplot(1,2,2)
plt.imshow(nbr, cmap='RdYlGn', vmin=-1, vmax=1)
plt.colorbar()
plt.title('NBR Sentinel-2')

plt.tight_layout()
plt.show()
