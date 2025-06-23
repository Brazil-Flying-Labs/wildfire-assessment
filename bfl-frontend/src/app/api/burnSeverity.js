// pages/api/burnSeverity.js

import ee from '@google/earthengine';

let isAuthenticated = false;

/**
 * 1) Cloud & Shadow Masking with s2cloudless
 * 2) Multi-Year Pre-Fire Baseline
 * 3) Single-Year Post-Fire
 * 4) Additional Indices: NDVI, NBR, EVI, NDWI, NBR2, BAI
 * 5) Example Threshold-Based Classification
 */

//-----------------------------------------------
// HELPER FUNCTIONS
//-----------------------------------------------

// a) Join Sentinel-2 SR with Cloud Probability
function joinS2Collections(srCol, cloudCol) {
  return ee.ImageCollection(
    ee.Join.saveFirst('cloud_prob').apply({
      primary: srCol,
      secondary: cloudCol,
      condition: ee.Filter.equals({
        leftField: 'system:index',
        rightField: 'system:index'
      })
    })
  );
}

// b) Cloud masking function
function maskCloudsAndShadows(image) {
  // Get the cloud probability image (saved as property 'cloud_prob')
  const cloudProb = ee.Image(image.get('cloud_prob'));
  const probability = cloudProb.select('probability');

  // Mask out pixels >30% cloud probability
  const isCloud = probability.gt(30);
  const cloudMask = isCloud.not();

  // Return the masked image
  return image.updateMask(cloudMask);
}

// c) Scale reflectance & add indices
function scaleAndAddIndices(image) {
  const scaled = image.select(['B2','B3','B4','B8','B11','B12'])
    .multiply(0.0001)
    .rename(['BLUE','GREEN','RED','NIR','SWIR1','SWIR2']);

  const blue  = scaled.select('BLUE');
  const green = scaled.select('GREEN');
  const red   = scaled.select('RED');
  const nir   = scaled.select('NIR');
  const swir1 = scaled.select('SWIR1');
  const swir2 = scaled.select('SWIR2');

  // Indices
  const ndvi = nir.subtract(red).divide(nir.add(red)).rename('NDVI');
  const nbr  = nir.subtract(swir2).divide(nir.add(swir2)).rename('NBR');
  const evi  = nir.subtract(red)
    .multiply(2.5)
    .divide(
      nir.add(red.multiply(6.0))
         .subtract(blue.multiply(7.5))
         .add(1.0)
    ).rename('EVI');
  const ndwi = green.subtract(nir).divide(green.add(nir)).rename('NDWI');
  const nbr2 = nir.subtract(swir1).divide(nir.add(swir1)).rename('NBR2');
  const bai  = ee.Image.constant(1).divide(
    (ee.Image.constant(0.1).subtract(red)).pow(2)
      .add(ee.Image.constant(0.06).subtract(nir).pow(2))
  ).rename('BAI');

  return scaled
    .addBands([ndvi, nbr, evi, ndwi, nbr2, bai])
    .copyProperties(image, image.propertyNames());
}

// d) Build multi-year baseline
function buildMultiYearBaseline(joinedCollection, years, startMMDD, endMMDD) {
  let combined = ee.ImageCollection([]);
  years.forEach(function(y) {
    const startDate = ee.Date(y + startMMDD);
    const endDate   = ee.Date(y + endMMDD);

    const col = joinedCollection
      .filterDate(startDate, endDate)
      .map(maskCloudsAndShadows)
      .map(scaleAndAddIndices);

    combined = combined.merge(col);
  });
  return combined.median();
}

//-----------------------------------------------
// MAIN HANDLER
//-----------------------------------------------
export default async function handler(req, res) {
  try {
    // Only accept POST
    if (req.method !== 'POST') {
      return res.status(405).json({ error: 'Use POST' });
    }

    // Parse request body
    // We allow the user to pass geometry, preFireYears, postFireYear, etc.
    // For simplicity, we default if not provided.
    const {
      geometry,
      preFireYears = [2020, 2021],
      preStartMMDD = '-07-01',
      preEndMMDD   = '-10-15',
      postFireYear = 2024,
      postStartMMDD = '-08-01',
      postEndMMDD   = '-10-15'
    } = JSON.parse(req.body);

    // Lazy auth
    if (!isAuthenticated) {
      const privateKey = JSON.parse(process.env.EE_CREDENTIALS || '{}');
      await new Promise((resolve, reject) => {
        ee.data.authenticateViaPrivateKey(
          privateKey,
          () => {
            ee.initialize(null, null, () => {
              isAuthenticated = true;
              resolve();
            }, reject);
          },
          reject
        );
      });
    }

    // Convert geometry to ee.Geometry
    const studyArea = ee.Geometry(geometry);

    // Load Sentinel-2 SR & Cloud Probability
    const s2SrCol = ee.ImageCollection('COPERNICUS/S2_SR')
      .filterBounds(studyArea);

    const s2CloudCol = ee.ImageCollection('COPERNICUS/S2_CLOUD_PROBABILITY')
      .filterBounds(studyArea);

    // Join them
    const joined = joinS2Collections(s2SrCol, s2CloudCol);

    // Build multi-year pre-fire
    const preFireImg = buildMultiYearBaseline(
      joined,
      preFireYears,
      preStartMMDD,
      preEndMMDD
    );

    // Build post-fire
    const startDatePost = ee.Date(postFireYear + postStartMMDD);
    const endDatePost   = ee.Date(postFireYear + postEndMMDD);
    const postFireImg = joined
      .filterDate(startDatePost, endDatePost)
      .map(maskCloudsAndShadows)
      .map(scaleAndAddIndices)
      .median();

    // Differences
    const dNDVI = preFireImg.select('NDVI').subtract(postFireImg.select('NDVI')).rename('dNDVI');
    const dNBR  = preFireImg.select('NBR').subtract(postFireImg.select('NBR')).rename('dNBR');

    // Example threshold classification
    // top-down OR logic
    const burnSeverity = ee.Image.cat([dNDVI, dNBR]).expression(
      "(dNDVI >= 0.3 || dNBR >= 0.3) ? 3" + 
      ": (dNDVI >= 0.2 || dNBR >= 0.2) ? 2" +
      ": (dNDVI >= 0.1 || dNBR >= 0.1) ? 1" +
      ": 0",
      { dNDVI: dNDVI, dNBR: dNBR }
    ).rename('burnSeverity');

    // Create a tile layer from burnSeverity
    const visParams = {
      min: 0,
      max: 3,
      palette: ['00FF00','FFFF00','FFA500','FF0000'] // 0=unburned..3=high burn
    };

    const mapObj = burnSeverity.getMap(visParams);
    const tileUrl = `https://earthengine.googleapis.com/map/${mapObj.mapid}/{z}/{x}/{y}?token=${mapObj.token}`;

    // Return JSON with tileUrl + map info
    return res.status(200).json({
      tileUrl,
      mapId: mapObj.mapid,
      token: mapObj.token
    });

  } catch (err) {
    console.error('Burn severity error:', err);
    return res.status(500).json({ error: err.message });
  }
}