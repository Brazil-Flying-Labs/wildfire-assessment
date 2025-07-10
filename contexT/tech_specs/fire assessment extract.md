# Fire Assessment Pipeline Documentation

## Process Overview – Pipeline 1

This Pipeline 1 aims to calculate NDVI and NBR to identify the area of interest for further processing. This area of interest should exclude regions with exposed soil, ensuring that only potentially vegetated and burned areas proceed to the next stages.

### Pipeline 1 Flowchart Description
The diagram shows a linear workflow starting with a scheduler that runs once a month. The process flows through several stages:
1. Sentinel-2 satellite data input (10-20m pixels with RGB, NIR, R, SWIR bands)
2. Multiband GeoTIFF storage
3. NDVI and NBR calculation
4. Selection of areas without exposed soil
5. Final multiband GeoTIFF and GeoJSON export

Each stage is represented by icons showing the data transformation from satellite imagery to processed geospatial files.

## 1. Sentinel-2

Sentinel-2 provides multispectral images with several bands. In this pipeline, we use:

| Band | Name | Resolution | Application |
|------|------|------------|-------------|
| B2 | Blue | 10 m | Visual (RGB) |
| B3 | Green | 10 m | Visual (RGB) |
| B4 | Red | 10 m | Visual (RGB), NDVI calculation |
| B8 | NIR (Near Infrared) | 10 m | NDVI and NBR calculation |
| B11 | SWIR (Short-Wave IR 1) | 20 m | NBR calculation |

**Note:** Bands with 20 m resolution (like B11) are resampled to 10 m to maintain consistency with the others.

## 2. Pull data using Sentinel Hub API

The Sentinel Hub API is used to download multispectral (multiband) images of the area of interest on a monthly basis. Use pre-filter to less than 30% clouds to make sure we have usable data.

## 3. Save Multiband GeoTIFF

The images are saved in multiband GeoTIFF format, containing all the required bands in a single georeferenced file, facilitating further processing.

## 4. NDVI (Normalized Difference Vegetation Index)

Detects healthy vegetation.

**Formula:**
```
NDVI = (NIR - Red) / (NIR + Red) = (B8 - B4) / (B8 + B4)
```

**Typical values:**
- Healthy vegetation: ~0.6 to 0.9
- Bare soil / no vegetation: ~0 to 0.2

## 5. NBR (Normalized Burn Ratio)

Detects burned areas by comparing vegetation reflectance (NIR) with charred biomass (SWIR).

**Formula:**
```
NBR = (NIR - SWIR) / (NIR + SWIR) = (B8 - B11) / (B8 + B11)
```

**Typical values:**
- Healthy vegetation: High NBR (~0.6 to 0.8)
- Burned area: Low NBR (~0 to -0.5)

NBR values above ~0.1 indicate a low probability of burning but do not guarantee vegetation presence (could be bare soil, agriculture, or built-up areas). Therefore, NDVI is used alongside NBR.

## 6. Select Areas without Exposed Soil

Filters are applied to remove exposed soil regions that were not burned, avoiding false positives.

NDVI and NBR are used together to improve accuracy:
- NDVI is great for distinguishing healthy vegetation from bare or degraded land.
- NBR is more sensitive to fire-related changes but can also respond to other disturbances (like harvesting or construction).

Combined logic helps:
- Reduce false positives (e.g., bare soil mistaken for burned areas)
- Distinguish between burned and naturally unvegetated areas

**Calculation:**
```python
exposed_soil = (
    (ndvi < 0.2) &  # Low NDVI → no vegetation
    (nbr > 0.1)     # High NBR → no fire evidence
)
```

Areas not marked as exposed soil continue through the pipeline as potential burned areas.

## 7. Export Multiband GeoTIFF and GeoJSON

In this step, the original GeoTIFF file is extended with three new raster layers, each containing essential derived data for mapping and analysis:

- **NDVI Layer:** Shows vegetation index values per pixel, assessing vegetation health.
- **NBR Layer:** Shows burn index values, useful for detecting fire-affected areas and severity.
- **Mask Layer:** A binary mask indicating relevant analysis areas:
  - 1 for vegetated areas possibly burned.
  - 0 for excluded areas like exposed soil, water bodies, or urban zones.

These layers are embedded in the same multiband GeoTIFF file, preserving georeferencing, spatial resolution, and raster format compatible with tools like QGIS.

Additionally, the binary mask can optionally be exported as a GeoJSON file, converting pixels with value 1 into vector polygons. This vector version facilitates visualization, overlay with other spatial data, and use in web platforms or geographic databases.

---

## Process Overview – Pipeline 2

This pipeline runs automatically once a month and is designed to process and compare georeferenced images (GeoTIFFs) from two consecutive months to monitor fire occurrence and severity.

### Pipeline 2 Flowchart Description
The diagram illustrates a more complex workflow that includes:
1. Storage of files from previous weeks/months
2. Data processing and comparison using Google Earth Engine API
3. Generation of multiband GeoTIFF and CSV reports
4. Web visualization tool for public access with filtering capabilities
5. Connection to Fundação Florestal for internal use
6. QGIS integration for advanced analysis

The workflow shows two main user paths: one for general public access through the web tool, and another for technical analysts using QGIS.

## 1. Data Storage

Multiband GeoTIFF satellite images for months N (current) and N-1 (previous) are stored in a local or cloud file system.

These files form the basis for detecting temporal changes in vegetation and land surface.

## 2. Monthly Comparison

An automated process compares the GeoTIFFs from months N and N-1 to:
- Detect significant vegetation cover changes — such as newly burned areas — by analyzing spectral indices (NDVI and NBR).
- Calculate change indices based on spectral data.
- Generate reports with extracted metrics.

**Note:** There should be a way to compare not only subsequent months, but any months you want. Ex: January against May.

## 3. Google Earth Engine API

Using the NDVI and NBR indices for two consecutive months, Google Earth Engine (GEE) is used to:

- Compute spectral deltas (ΔNDVI and ΔNBR), representing temporal variations between images.
- Generate change maps to visualize spatially impacted areas.
- Classify fire severity based on ΔNBR value ranges:
  - Light
  - Moderate
  - Severe
- Quantify the total affected area (in hectares), distinguishing between:
  - New burned areas (not affected in the previous month)
  - Recurring areas (previously affected)
- Analyze temporal trends in burned area extent, highlighting monthly changes (increase, decrease, or stability) to support preventive or corrective actions.

**Possible deliverables generated by GEE:**

| Product Type | Content | Format |
|--------------|---------|---------|
| Continuous GeoTIFFs | ΔNDVI, ΔNBR per pixel | .tif |
| Thematic Maps | Fire severity classification | .tif / .png |
| Vectors | Polygons per severity level | .geojson |
| Reports | Impacted area, temporal comparison | .csv / .json |

## 4. Result Storage

Processing outputs (multiband images, ΔNDVI/ΔNBR, thematic maps, and CSV tables) are saved again in the file system or cloud.

## 5. Web Visualization Tool

A public web tool. Anyone can access it to view and download available data. Target audience includes citizens, NGOs, journalists, etc.

**Please include a zoom feature.**

The tool allows:
- Filtering by time period, data source, burn severity, among others.
- Comparing different months.
- Direct download of files (images, maps, reports).

## 6. QGIS

For more in-depth analysis, the images and generated products are compatible with QGIS, a free Geographic Information System (GIS) software.

This step targets analysts and technicians from the Forestry Foundation, enabling:
- High-precision georeferenced visualization.
- Integration with other geospatial layers.
- Support for decision-making and technical report preparation.

**Link to Drawio:**
https://app.diagrams.net/#G19vjkpPU2DiJxExa5g5cEmvi-D8VgmZ24#%7B%22pageId%22%3A%22wPnxvt_lScqypTI62Ptz%22%7D

---

## Portuguese Version - Original Version

### Visão Geral do Processo - Pipeline 1

Esta Pipeline 1 tem o objetivo de calcular NDVI e NBR para identificar a área de interesse para processamentos posteriores. Essa área de interesse deve excluir regiões com solo exposto, garantindo que apenas áreas potencialmente vegetadas e queimadas sigam para as próximas etapas. Os resultados intermediários podem ser visualizados em ferramentas como o QGIS.

### Diagrama do Pipeline 1 (Versão em Português)
O diagrama mostra o mesmo fluxo da versão em inglês, mas com rótulos em português. Inclui:
1. Agendador que executa uma vez por mês
2. Dados do Sentinel-2 (RGB, NIR, R, bandas SWIR)
3. GeoTIFF multibanda
4. Cálculo de NDVI e NBR
5. Seleção de áreas sem solo exposto
6. Armazenamento final em GeoTIFF multibanda e GeoJSON

## 1. Sentinel-2

O Sentinel-2 fornece imagens multiespectrais com várias bandas. Neste pipeline, usamos:

| Banda | Nome | Resolução | Aplicação |
|-------|------|-----------|-----------|
| B2 | Blue | 10 m | Visual (RGB) |
| B3 | Green | 10 m | Visual (RGB) |
| B4 | Red | 10 m | Visual (RGB), cálculo de NDVI |
| B8 | NIR (Near Infrared) | 10 m | Cálculo de NDVI e NBR |
| B11 | SWIR (Short-Wave Infrared 1) | 20 m | Cálculo de NBR |

Vale mencionar que as bandas com resolução de 20 m (como a B11) são reamostradas para 10 m para manter a consistência com as demais.

## 2. Pull data usando Sentinel Hub API

Usa-se a Sentinel Hub API para baixar as imagens multiespectrais (multibanda) da área de interesse, com frequência mensal.

## 3. Salvar Multiband geoTIFF

As imagens são salvas no formato GeoTIFF multibanda, contendo todas as bandas necessárias em um único arquivo georreferenciado, facilitando o processamento posterior.

## 4. NDVI (Normalized Difference Vegetation Index)

Detecta vegetação saudável.

**Fórmula:**
```
NDVI = (NIR - Red) / (NIR + Red) = (B8 - B4) / (B8 + B4)
```

**Valores:**
- Vegetação saudável: ~0.6 a 0.9
- Sem vegetação / solo exposto: ~0 a 0.2

## 5. NBR (Normalized Burn Ratio)

Detecta áreas queimadas, comparando a reflectância da vegetação (NIR) com a da biomassa carbonizada (SWIR).

**Fórmula:**
```
NBR = (NIR - SWIR) / (NIR + SWIR) = (B8 - B11) / (B8 + B11)
```

**Valores:**
- Vegetação saudável: NBR alto (~0.6 a 0.8)
- Área queimada: NBR baixo (~0 a -0.5)

Valores de NBR acima de ~0.1 indicam baixa probabilidade de queimada, mas não garantem que a área esteja vegetada. Pode haver solo nu, agricultura ou áreas construídas. Por isso, o NDVI é usado em conjunto.

## 6. Selecionar áreas sem solo exposto

Aqui são aplicados filtros para remover regiões com solo exposto que não foram queimadas, evitando falsos positivos.

Utilizamos NDVI e NBR em conjunto para aumentar a acurácia:
- NDVI é ótimo para distinguir vegetação saudável de solo nu ou áreas degradadas.
- NBR é mais sensível a alterações causadas por queimadas, mas também responde a outras perturbações (como colheitas e construção civil).

Quando combinados, eles ajudam a:
- Reduzir falsos positivos, como solo exposto sendo confundido com áreas queimadas.
- Distingue áreas queimadas de áreas naturalmente desprovidas de vegetação.

**Cálculo:**
```python
solo_exposto = (
    (ndvi < 0.2) &  # NDVI baixo → ausência de vegetação
    (nbr > 0.1)     # NBR alto → ausência de sinais de queimada
)
```

As áreas não marcadas como solo exposto seguem no pipeline como candidatas a áreas queimadas. Essa máscara é adicionada como uma camada adicional ao GeoTIFF para posterior visualização e refinamento no QGIS.

## 7. Exportar Multiband geoTIFF e geoJSON

Nesta etapa, o arquivo GeoTIFF original será expandido com três novas camadas raster, cada uma contendo uma informação derivada essencial para o mapeamento e análise:

- **Camada NDVI:** contém os valores do índice de vegetação (NDVI) para cada pixel, permitindo avaliar a saúde da vegetação em toda a área de interesse.
- **Camada NBR:** armazena os valores do índice de queimada (NBR), úteis para detectar áreas afetadas por fogo e sua severidade.
- **Camada de Máscara:** representa uma máscara binária que indica as áreas relevantes para análise, com:
  - 1 para regiões vegetadas possivelmente queimadas,
  - 0 para áreas excluídas, como solo exposto, corpos d'água ou zonas urbanas.

Essas camadas são incorporadas no mesmo arquivo GeoTIFF multibanda, mantendo a georreferência, resolução espacial e formato raster compatível com ferramentas como o QGIS.

Além disso, opcionalmente, a máscara binária também pode ser exportada como um arquivo GeoJSON, convertendo os pixels com valor 1 em polígonos vetoriais. Essa versão vetorial facilita a visualização, a sobreposição com outros dados espaciais e o uso em plataformas web ou bancos de dados geográficos.

---

### Visão Geral do Processo - Pipeline 2

Esta pipeline é executada automaticamente uma vez por mês e tem como objetivo processar e comparar imagens georreferenciadas (GeoTIFFs) de dois meses consecutivos, visando monitorar a ocorrência e a severidade de queimadas.

### Diagrama do Pipeline 2 (Versão em Português)
O diagrama em português mostra a mesma estrutura complexa da versão em inglês, incluindo:
1. Armazenamento de arquivos de semanas/meses anteriores
2. Processamento e comparação usando Google Earth Engine API
3. Geração de GeoTIFF multibanda e relatórios CSV
4. Ferramenta de visualização web para acesso público
5. Conexão com a Fundação Florestal
6. Integração com QGIS para análise avançada

## 1. Armazenamento de dados

As imagens de satélite no formato GeoTIFF multibanda, correspondentes aos meses N (atual) e N-1 (anterior), são armazenadas em um sistema de arquivos local ou em nuvem.

Esses arquivos constituem a base para a detecção de mudanças temporais na vegetação e na superfície terrestre.

## 2. Comparação Mensal

Um processo automatizado realiza a comparação entre os GeoTIFFs dos meses N e N-1, com o objetivo de:
- Detectar alterações significativas na cobertura vegetal — como áreas recém-queimadas — por meio da análise dos índices espectrais (NDVI e NBR).
- Calcular índices de mudança a partir dos dados espectrais;
- Gerar relatórios com as métricas extraídas.

## 3. Google Earth Engine API

Utilizando os índices NDVI (Normalized Difference Vegetation Index) e NBR (Normalized Burn Ratio) gerados para as dois meses consecutivos, o GEE é empregado para:

- Calcular os deltas espectrais (ΔNDVI e ΔNBR), que representam as variações temporais entre as imagens;
- Produzir mapas de mudança (change maps) para visualização espacial das áreas impactadas;
- Classificar a severidade das queimadas, com base em faixas estabelecidas do ΔNBR:
  - Leve
  - Moderada
  - Severa
- Quantificar a área total afetada (em hectares), distinguindo entre:
  - Novas áreas queimadas (não afetadas no mês anterior);
  - Áreas reincidentes (afetadas no mês anterior);
- Avaliar tendências temporais na extensão das áreas queimadas, destacando variações mensais (aumento, redução ou estabilidade) e subsidiando ações preventivas ou corretivas.

**Possíveis deliverables gerados pelo GEE:**

| Tipo de Produto | Conteúdo | Formato |
|-----------------|----------|---------|
| GeoTIFFs contínuos | ΔNDVI, ΔNBR por pixel | .tif |
| Mapas temáticos | Severidade da queimada | .tif / .png |
| Vetores | Polígonos por severidade | .geojson |
| Relatórios | Área impactada, comparação temporal | .csv / .json |

## 4. Armazenamento de Resultados

As saídas do processamento (imagens multibanda, ΔNDVI/ΔNBR, mapas temáticos e tabelas CSV) são armazenadas novamente no sistema de arquivos ou nuvem.

## 5. Web Visualization Tool

Uma ferramenta web acessível ao público em geral. Qualquer pessoa pode acessar a ferramenta de visualização e baixar os dados disponíveis. Público-alvo são cidadãos, ONGs, jornalistas, etc.

A ferramenta possibilita:
- Aplicação de filtros por período, fonte dos dados, severidade da queimada, entre outros;
- Comparação entre diferentes meses;
- Download direto dos arquivos de interesse (imagens, mapas e relatórios).

## 6. QGIS

Para análises mais detalhadas, as imagens e produtos gerados são compatíveis com o QGIS, um software livre de Sistema de Informação Geográfica (SIG).

Essa etapa é voltada para analistas e técnicos da Fundação Florestal, permitindo:
- Visualização georreferenciada de alta precisão;
- Integração com outras camadas geoespaciais;
- Suporte à tomada de decisão e à elaboração de relatórios técnicos.