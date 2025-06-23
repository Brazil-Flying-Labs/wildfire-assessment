"use client";

import { MapContainer, TileLayer, ZoomControl, useMap } from 'react-leaflet';
import { useEffect, useState } from 'react';
import 'leaflet/dist/leaflet.css';
import { Card, CardContent } from './ui/card';

const CDN = process.env.NEXT_PUBLIC_CDN!;
const DEFAULT_SCENE = 'test-area4';
const DEFAULT_DATE = '2023-05-15';

export interface SatelliteMapProps {
  className?: string;
  regionId?: string;
  fromDate?: Date;
  toDate?: Date;
  enabledLayers?: string[];
  imageUrls?: Record<string, Record<string, string>>;
  diffUrls?: { ndvi1: string; ndvi2: string } | null;
  tiTilerUrl?: string;
  tiTilerCdnUrl?: string;
}

// Component to handle auto-centering the map on view change
function SetViewOnChange({ center, zoom }: { center: [number, number], zoom: number }) {
  const map = useMap();
  
  useEffect(() => {
    map.setView(center, zoom);
  }, [center, zoom, map]);
  
  return null;
}

export function SatelliteMap({
  className,
  regionId = DEFAULT_SCENE,
  fromDate,
  toDate,
  enabledLayers,
  imageUrls,
  diffUrls,
  tiTilerUrl,
  tiTilerCdnUrl = CDN
}: SatelliteMapProps) {
  const [layer, setLayer] = useState<'rgb' | 'ndvi' | 'nbr'>('rgb');
  const actualRegionId = regionId || DEFAULT_SCENE;
  const actualDate = toDate ? toDate.toISOString().split('T')[0] : DEFAULT_DATE;

  const getTileUrl = () =>
    `${tiTilerCdnUrl || CDN}/${actualRegionId}/${actualDate}/${layer}.tif/tiles/{z}/{x}/{y}.png`;

  useEffect(() => {
    const L = require('leaflet');
    delete L.Icon.Default.prototype._getIconUrl;
    L.Icon.Default.mergeOptions({
      iconRetinaUrl: '/images/marker-icon-2x.png',
      iconUrl: '/images/marker-icon.png',
      shadowUrl: '/images/marker-shadow.png',
    });
  }, []);

  return (
    <div className={`w-full h-[600px] rounded-lg overflow-hidden ${className || ''}`}>
      <MapContainer 
        center={[-21.57, -47.85]} 
        zoom={12} 
        zoomControl={false} 
        style={{ height: '100%', width: '100%' }}
      >
        <ZoomControl position="bottomright" />
        <TileLayer
          attribution="© OpenStreetMap contributors"
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <TileLayer
          attribution={`Satellite: ${layer.toUpperCase()}`}
          url={getTileUrl()}
          opacity={0.8}
        />
      </MapContainer>

      <div className="mt-4 flex gap-3">
        <button 
          onClick={() => setLayer('rgb')} 
          className={`px-3 py-2 rounded ${layer === 'rgb' ? 'bg-green-600 text-white' : 'bg-gray-200'}`}
        >
          Natural Color
        </button>
        <button 
          onClick={() => setLayer('ndvi')} 
          className={`px-3 py-2 rounded ${layer === 'ndvi' ? 'bg-green-600 text-white' : 'bg-gray-200'}`}
        >
          Vegetation (NDVI)
        </button>
        <button 
          onClick={() => setLayer('nbr')} 
          className={`px-3 py-2 rounded ${layer === 'nbr' ? 'bg-green-600 text-white' : 'bg-gray-200'}`}
        >
          Burn Ratio (NBR)
        </button>
      </div>
    </div>
  );
}

// Also export as default for compatibility
export default SatelliteMap;
