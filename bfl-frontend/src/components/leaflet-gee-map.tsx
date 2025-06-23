"use client";

import { useEffect, useRef, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// Define props interface
export interface LeafletGEEMapProps {
  className?: string;
  regionId?: string;
  center?: [number, number]; // [lat, lng]
  zoom?: number;
  initialLayer?: 'rgb' | 'ndvi' | 'nbr';
}

export default function LeafletGEEMap({
  className,
  regionId = 'luiz-antonio',
  center = [-21.57, -47.85], // Default to Luiz Antonio coordinates
  zoom = 12,
  initialLayer = 'rgb'
}: LeafletGEEMapProps) {
  const mapRef = useRef<HTMLDivElement>(null);
  const leafletMapRef = useRef<L.Map | null>(null);
  const [layer, setLayer] = useState<'rgb' | 'ndvi' | 'nbr'>(initialLayer);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Initialize Leaflet map
  useEffect(() => {
    if (!mapRef.current) return;
    
    console.log('Initializing Leaflet map...');
    
    // Check if map already exists
    if (leafletMapRef.current) {
      leafletMapRef.current.remove();
    }
    
    try {
      // Create Leaflet map
      const map = L.map(mapRef.current).setView(center, zoom);
      
      // Add OpenStreetMap as base layer
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
      }).addTo(map);
      
      // Store map reference
      leafletMapRef.current = map;
      
      // Add Sentinel-2 layer from Google Earth Engine
      addSentinelLayer(map);
      
      setLoading(false);
    } catch (err) {
      console.error('Error initializing Leaflet map:', err);
      setError(`Failed to initialize map: ${err instanceof Error ? err.message : String(err)}`);
      setLoading(false);
    }
    
    // Cleanup function
    return () => {
      if (leafletMapRef.current) {
        leafletMapRef.current.remove();
        leafletMapRef.current = null;
      }
    };
  }, [center, zoom]);
  
  // Update map when layer changes
  useEffect(() => {
    if (leafletMapRef.current) {
      addSentinelLayer(leafletMapRef.current);
    }
  }, [layer]);
  
  // Function to add Sentinel-2 layer
  const addSentinelLayer = (map: L.Map) => {
    // Remove existing overlay layers
    map.eachLayer((layer) => {
      if (layer instanceof L.TileLayer && !(layer as any).isBaseLayer) {
        map.removeLayer(layer);
      }
    });
    
    // Define layer URLs based on selected visualization
    let tileUrl = '';
    let layerName = '';
    
    switch (layer) {
      case 'rgb':
        // Example URL for Sentinel-2 RGB composite from a public tile server
        tileUrl = 'https://services.sentinel-hub.com/ogc/wms/your-instance-id?service=WMS&request=GetMap&layers=TRUE-COLOR&styles=&format=image/jpeg&transparent=true&version=1.1.1&width=256&height=256&srs=EPSG:3857&bbox={bbox}';
        layerName = 'Sentinel-2 RGB';
        break;
      case 'ndvi':
        // Example URL for NDVI visualization
        tileUrl = 'https://services.sentinel-hub.com/ogc/wms/your-instance-id?service=WMS&request=GetMap&layers=NDVI&styles=&format=image/jpeg&transparent=true&version=1.1.1&width=256&height=256&srs=EPSG:3857&bbox={bbox}';
        layerName = 'NDVI';
        break;
      case 'nbr':
        // Example URL for NBR visualization
        tileUrl = 'https://services.sentinel-hub.com/ogc/wms/your-instance-id?service=WMS&request=GetMap&layers=NBR&styles=&format=image/jpeg&transparent=true&version=1.1.1&width=256&height=256&srs=EPSG:3857&bbox={bbox}';
        layerName = 'NBR';
        break;
    }
    
    // For demonstration, we'll use a placeholder message instead of actual tiles
    // In a real implementation, you would replace the URLs above with actual Earth Engine tile URLs
    
    // Add a marker to show something is working
    L.marker(center).addTo(map)
      .bindPopup(`This is a placeholder for ${layerName} visualization.<br>In a real implementation, this would show actual satellite imagery.`)
      .openPopup();
      
    console.log(`Added placeholder for ${layerName} visualization`);
  };

  return (
    <div className={`relative ${className || ''}`}>
      {/* Map container */}
      <div 
        ref={mapRef} 
        className="w-full h-[600px] rounded-lg overflow-hidden"
      />
      
      {/* Loading overlay */}
      {loading && (
        <div className="absolute inset-0 flex items-center justify-center bg-black bg-opacity-30 z-10">
          <div className="bg-white p-4 rounded-md shadow-md flex items-center space-x-2">
            <Loader2 className="h-5 w-5 animate-spin text-primary" />
            <p>Loading map...</p>
          </div>
        </div>
      )}
      
      {/* Error message */}
      {error && (
        <div className="absolute inset-0 flex items-center justify-center bg-black bg-opacity-30 z-10">
          <div className="bg-white p-4 rounded-md shadow-md">
            <p className="text-red-500">{error}</p>
            <p className="text-sm mt-2">Check browser console for more details</p>
          </div>
        </div>
      )}
      
      {/* Controls */}
      <div className="mt-4 flex flex-wrap gap-3 justify-between">
        <div className="flex gap-2">
          <Button 
            onClick={() => setLayer('rgb')} 
            variant={layer === 'rgb' ? 'default' : 'outline'}
          >
            Natural Color
          </Button>
          <Button 
            onClick={() => setLayer('ndvi')} 
            variant={layer === 'ndvi' ? 'default' : 'outline'}
          >
            Vegetation (NDVI)
          </Button>
          <Button 
            onClick={() => setLayer('nbr')} 
            variant={layer === 'nbr' ? 'default' : 'outline'}
          >
            Burn Ratio (NBR)
          </Button>
        </div>
        
        <Badge variant="outline" className="px-2 py-1">
          Note: This is a placeholder map. In production, it would display actual satellite imagery.
        </Badge>
      </div>
    </div>
  );
}
