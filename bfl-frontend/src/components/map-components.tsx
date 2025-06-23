"use client";

import { useEffect, useState } from 'react';
import { MapContainer, TileLayer, ZoomControl, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';

// Define the props for the MapComponent
interface MapComponentProps {
  center: [number, number];
  zoom: number;
  regionId: string;
  layer: 'rgb' | 'ndvi' | 'nbr';
  cdnUrl: string;
  date: string;
}

// This component updates the map view when props change
function MapUpdater({ center, zoom }: { center: [number, number]; zoom: number }) {
  const map = useMap();
  
  useEffect(() => {
    map.setView(center, zoom);
  }, [map, center, zoom]);
  
  return null;
}

// Main map component with tile layer
export function MapComponent({ 
  center, 
  zoom, 
  regionId, 
  layer, 
  cdnUrl, 
  date 
}: MapComponentProps) {
  const [error, setError] = useState<string | null>(null);
  
  // Construct the tile URL based on the props
  const getTileUrl = () => 
    `${cdnUrl}/${regionId}/${date}/${layer}.tif/tiles/{z}/{x}/{y}.png`;
  
  useEffect(() => {
    // Reset error when layer, region, or date changes
    setError(null);
  }, [layer, regionId, date]);

  // Initialize Leaflet icon to prevent missing marker icons
  useEffect(() => {
    const L = require('leaflet');
    delete L.Icon.Default.prototype._getIconUrl;
    
    L.Icon.Default.mergeOptions({
      iconRetinaUrl: 'https://unpkg.com/leaflet@1.7.1/dist/images/marker-icon-2x.png',
      iconUrl: 'https://unpkg.com/leaflet@1.7.1/dist/images/marker-icon.png',
      shadowUrl: 'https://unpkg.com/leaflet@1.7.1/dist/images/marker-shadow.png',
    });
  }, []);

  return (
    <>
      {error && (
        <div className="absolute inset-0 flex items-center justify-center bg-gray-100 bg-opacity-80 z-10">
          <div className="bg-white p-4 rounded-md shadow-md">
            <p className="text-red-500">{error}</p>
          </div>
        </div>
      )}
      
      <MapContainer 
        center={center} 
        zoom={zoom} 
        style={{ height: '100%', width: '100%' }}
        zoomControl={false}
      >
        <ZoomControl position="bottomright" />
        <MapUpdater center={center} zoom={zoom} />
        
        <TileLayer
          url={getTileUrl()}
          attribution="&copy; BFL Satellite Imagery"
          errorOverlayUrl="https://via.placeholder.com/256x256?text=No+Image"
          onError={() => setError(`Failed to load ${layer.toUpperCase()} imagery for the selected date.`)}
        />
      </MapContainer>
    </>
  );
}
