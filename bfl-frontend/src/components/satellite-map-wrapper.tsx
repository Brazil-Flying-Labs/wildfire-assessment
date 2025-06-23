"use client";

import { useState, useEffect } from 'react';
import dynamic from 'next/dynamic';
import { Card, CardContent } from './ui/card';

// Import Leaflet components with dynamic import to avoid SSR issues
const MapWithNoSSR = dynamic(
  () => import('./map-components').then((mod) => mod.MapComponent),
  { ssr: false }
);

// Define props interface
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

export default function SatelliteMapWrapper({
  className,
  regionId = 'test-area4',
  fromDate,
  toDate,
  enabledLayers,
  imageUrls,
  diffUrls,
  tiTilerUrl,
  tiTilerCdnUrl = process.env.NEXT_PUBLIC_CDN
}: SatelliteMapProps) {
  const [layer, setLayer] = useState<'rgb' | 'ndvi' | 'nbr'>('rgb');
  
  const cdnUrl = tiTilerCdnUrl || process.env.NEXT_PUBLIC_CDN || 'https://d3nl71iv3sr2rn.cloudfront.net';
  const actualDate = toDate ? toDate.toISOString().split('T')[0] : '2023-05-15';
  
  return (
    <div className={`w-full h-[600px] rounded-lg overflow-hidden ${className || ''}`}>
      <MapWithNoSSR 
        center={[-21.57, -47.85]}
        zoom={12}
        regionId={regionId}
        layer={layer}
        cdnUrl={cdnUrl}
        date={actualDate}
      />
      
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
