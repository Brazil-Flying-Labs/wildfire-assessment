import rasterio
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm
import matplotlib.patches as mpatches

# Funções de cálculo
def ndvi(nir, red):
    return (nir - red) / (nir + red + 1e-10)

def nbr(nir, swir):
    return (nir - swir) / (nir + swir + 1e-10)

def rbr(dnbr, nbr_pre):
    return dnbr / np.sqrt(np.abs(nbr_pre) + 1e-10)

# Leitura das bandas
def ler_banda(path):
    with rasterio.open(path) as src:
        return src.read(1).astype('float32'), src.profile

nir_b, meta = ler_banda(r"imagens\nir_antes.tiff")
swir_b, _ = ler_banda(r"imagens\swir_antes.tiff")
red_b, _ = ler_banda(r"imagens\red_antes.tiff")

nir_a, _ = ler_banda(r"imagens\nir_depois.tiff")
swir_a, _ = ler_banda(r"imagens\swir_depois.tiff")
red_a, _ = ler_banda(r"imagens\red_depois.tiff")

# Índices
ndvi_b = ndvi(nir_b, red_b)
ndvi_a = ndvi(nir_a, red_a)
dndvi = ndvi_b - ndvi_a

nbr_b = nbr(nir_b, swir_b)
nbr_a = nbr(nir_a, swir_a)
dnbr = nbr_b - nbr_a
rbr_map = rbr(dnbr, nbr_b)

# Classificação da queimada (exemplo com dNBR)
def classificar_dnbr(dnbr):
    classes = np.zeros(dnbr.shape, dtype=np.uint8)

    classes[dnbr < -0.1] = 1   # Regeneração
    classes[(dnbr >= -0.1) & (dnbr < 0.1)] = 2  # Sem mudança
    classes[(dnbr >= 0.1) & (dnbr < 0.27)] = 3  # Queimada baixa
    classes[(dnbr >= 0.27) & (dnbr < 0.44)] = 4  # Queimada moderada
    classes[(dnbr >= 0.44) & (dnbr < 0.66)] = 5  # Moderadamente severa
    classes[dnbr >= 0.66] = 6  # Alta severidade

    return classes

mapa_classificado = classificar_dnbr(dnbr)

# Salvar resultado
meta.update(dtype='uint8', count=1)

with rasterio.open("mapa_queimada.tiff", 'w', **meta) as dst:
    dst.write(mapa_classificado, 1)

# Paleta de cores e rótulos baseada na imagem fornecida
cores = ['black',  # 0 - Sem dados (opcional)
         '#00A600',  # 1 - Regeneração (Unburned)
         '#FFFF00',  # 2 - Baixa severidade (Low)
         '#FFA500',  # 3 - Moderada (Moderate)
         '#FF0000',  # 4 - Alta (High)
         '#800080']  # 5 - Muito alta (Very High)

rotulos = [
    "Sem dados", "Unburned", "Low Severity", 
    "Moderate Severity", "High Severity", "Very High Severity"
]

# Colormap e limites das classes
cmap = ListedColormap(cores)
bounds = [0, 1, 2, 3, 4, 5, 6]
norm = BoundaryNorm(bounds, len(cores))

# Visualização
plt.figure(figsize=(10, 8))
img = plt.imshow(mapa_classificado, cmap=cmap, norm=norm)
plt.title("Mapa de Severidade da Queimada (dNBR)", fontsize=14)
plt.axis('off')

# Criar legenda manual
patches = [mpatches.Patch(color=cores[i], label=rotulos[i]) for i in range(1, len(cores))]  # ignora "Sem dados"
plt.legend(handles=patches, loc='lower center', bbox_to_anchor=(0.5, -0.1),
           ncol=3, frameon=False, fontsize=10)

plt.tight_layout()
plt.show()
