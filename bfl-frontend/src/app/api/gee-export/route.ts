/**
 * STAC thumbnail proxy — AWS‑only, no GEE
 * ---------------------------------------
 * POST /api/gee-export
 * Body:
 *   {
 *     "region": [-48,-22,-47,-21],        // bbox [west,south,east,north]  OR GeoJSON Polygon
 *     "startDate": "2025-05-15",
 *     "endDate":   "2025-05-20"
 *   }
 *
 * Response 200:
 *   {
 *     success: true,
 *     thumbnailUrl: "https://sentinel-cogs.s3.us-west-2.amazonaws.com/...jpg",
 *     cloudCover: 17.88,
 *     sceneId: "S2A_33KWP_20250517_0_L2A"
 *   }
 */

import { NextResponse } from 'next/server';

/* ---------- helper -------------------------------------------------- */
function jsonError(
  msg: string,
  status = 500,
  extra: Record<string, unknown> = {}
) {
  return NextResponse.json({ success: false, error: msg, ...extra }, { status });
}

/* ---------- handler -------------------------------------------------- */
export async function POST(request: Request) {
  /* 1️⃣  Parse body */
  let body: any;
  try {
    body = await request.json();
  } catch {
    return jsonError('Invalid JSON body', 400);
  }

  const {
    region,
    startDate = '2025-05-01',
    endDate = '2025-05-31',
  } = body || {};

  // Ensure full RFC 3339 date‑times (adds midnight / end‑of‑day Z if only a date is provided)
  function toRFC3339(dateStr: string, endOfDay = false) {
    if (dateStr.includes('T')) return dateStr;            // already RFC3339
    return endOfDay
      ? `${dateStr}T23:59:59Z`
      : `${dateStr}T00:00:00Z`;
  }

  const isoStart = toRFC3339(startDate);
  const isoEnd   = toRFC3339(endDate, true);

  // Allow simple place-name strings by geocoding with Nominatim
  async function nameToBbox(name: string): Promise<[number, number, number, number] | null> {
    const url = `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(
      name
    )}&format=json&limit=1`;
    const res = await fetch(url, { headers: { 'User-Agent': 'bfl-demo/1.0' } });
    if (!res.ok) return null;
    const arr: any[] = await res.json();
    if (!arr.length) return null;
    const [south, north, west, east] = arr[0].boundingbox.map(parseFloat);
    return [west, south, east, north];
  }

  let finalRegion = region;
  if (!region) {
    return jsonError('"region" (bbox, GeoJSON, or place-name string) is required', 400);
  }
  if (typeof region === 'string') {
    const bbox = await nameToBbox(region);
    if (!bbox) {
      return jsonError(`Could not geocode place-name "${region}"`, 400);
    }
    finalRegion = bbox;
  }

  /* 2️⃣  Build STAC search payload */
  const stacPayload: Record<string, any> = {
    collections: ['sentinel-2-l2a'],
    datetime: `${isoStart}/${isoEnd}`,
    limit: 10,
    query: { 'eo:cloud_cover': { lt: 60 } },
    sortby: [{ field: 'properties.eo:cloud_cover', direction: 'asc' }],
  };

  if (Array.isArray(finalRegion) && finalRegion.length === 4) {
    stacPayload.bbox = finalRegion;
  } else {
    stacPayload.intersects = finalRegion; // assume GeoJSON Polygon
  }

  /* 3️⃣  Call the Earth-Search STAC API */
  const stacRes = await fetch(
    'https://earth-search.aws.element84.com/v1/search',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(stacPayload),
    }
  );

  if (!stacRes.ok) {
    let errBody: any = {};
    try {
      errBody = await stacRes.json();
    } catch {
      errBody = { message: await stacRes.text() };
    }
    console.error('STAC search failed', stacRes.status, errBody);
    return jsonError('STAC search failed', 502, {
      status: stacRes.status,
      stacError: errBody,
      payload: stacPayload,
      hint: 'Open the "Response" tab in dev‑tools to see stacError & payload for troubleshooting.'
    });
  }

  const { features = [] } = await stacRes.json();
  if (!features.length) {
    return jsonError('No Sentinel-2 scene found', 404);
  }

  const scene = features[0];
  const cloudCover = scene.properties['eo:cloud_cover'] as number;
  const thumbUrl = scene.assets?.thumbnail?.href as string | undefined;

  if (!thumbUrl) {
    return jsonError('Scene lacks thumbnail asset', 500);
  }

  /* 4️⃣  Respond with the thumbnail URL */
  return NextResponse.json({
    success: true,
    thumbnailUrl: thumbUrl,
    cloudCover,
    sceneId: scene.id,
  });
}