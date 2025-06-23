"use client";

import { useEffect, useRef, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Calendar } from '@/components/ui/calendar';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { format, subDays } from 'date-fns';
import { CalendarIcon, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

// Define props interface
export interface SimpleGEEMapProps {
  className?: string;
  regionId?: string;
  center?: [number, number]; // [lat, lng]
  zoom?: number;
  initialLayer?: 'rgb' | 'ndvi' | 'nbr';
}

export default function SimpleGEEMap({
  className,
  regionId = 'luiz-antonio',
  center = [-21.57, -47.85], // Default to Luiz Antonio coordinates
  zoom = 12,
  initialLayer = 'rgb'
}: SimpleGEEMapProps) {
  const mapRef = useRef<HTMLDivElement>(null);
  const [layer, setLayer] = useState<'rgb' | 'ndvi' | 'nbr'>(initialLayer);
  const [date, setDate] = useState<Date>(new Date());
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [mapInitialized, setMapInitialized] = useState<boolean>(false);
  const [cloudCover, setCloudCover] = useState<number | null>(null);

  // Initialize Google Earth Engine and map
  useEffect(() => {
    // First, check if we already have the Earth Engine API loaded
    if ((window as any).ee) {
      console.log('Earth Engine API already loaded, initializing...');
      initializeEarthEngine();
      return;
    }

    // Use the Google Maps Platform loader approach
    const loadEarthEngineAPI = () => {
      console.log('Setting up Earth Engine API loader...');
      
      // Create a script to load the Google Maps Platform loader
      const loaderScript = document.createElement('script');
      loaderScript.src = 'https://www.gstatic.com/external_hosted/loader/loader.js';
      loaderScript.async = true;
      
      loaderScript.onload = () => {
        console.log('Google loader script loaded, loading Earth Engine...');
        
        // Now use the loader to load Earth Engine
        try {
          const google = (window as any).google;
          if (!google || !google.load) {
            throw new Error('Google loader not available');
          }
          
          // Load the Earth Engine API
          google.load('earth', '1', {
            callback: function() {
              console.log('Earth Engine loaded via Google loader');
              initializeEarthEngine();
            },
            other_params: 'sensor=false'
          });
        } catch (err) {
          console.error('Error loading Earth Engine via Google loader:', err);
          setError(`Failed to load Earth Engine: ${err instanceof Error ? err.message : String(err)}`);
          setLoading(false);
        }
      };
      
      loaderScript.onerror = () => {
        console.error('Failed to load Google loader script');
        setError('Failed to load Google loader script');
        setLoading(false);
      };
      
      document.body.appendChild(loaderScript);
    };
    
    loadEarthEngineAPI();

    return () => {
      // No specific cleanup needed
    };
  }, []);

  // Function to initialize Earth Engine
  const initializeEarthEngine = async () => {
    try {
      console.log('Initializing Earth Engine...');
      const ee = (window as any).ee;
      
      if (!ee) {
        console.error('Earth Engine API not found in window object');
        setError('Earth Engine API not loaded');
        setLoading(false);
        return;
      }

      // Initialize with anonymous access for development
      await ee.initialize(null, null, () => {
        console.log('Earth Engine initialized successfully');
        setMapInitialized(true);
        renderMap();
      }, (err: Error) => {
        console.error('Earth Engine initialization error:', err);
        setError(`Earth Engine initialization failed: ${err.message}`);
        setLoading(false);
      });
      
    } catch (error) {
      console.error('Error in initializeEarthEngine:', error);
      setError(`Failed to initialize Google Earth Engine: ${error instanceof Error ? error.message : String(error)}`);
      setLoading(false);
    }
  };

  // Function to render the map
  const renderMap = () => {
    if (!mapInitialized || !mapRef.current) {
      console.log('Map not ready for rendering');
      return;
    }

    try {
      console.log('Rendering map...');
      const ee = (window as any).ee;
      
      // Create a simple demo map
      const map = new ee.Map(mapRef.current);
      
      // Set map center and zoom
      map.setCenter(center[1], center[0], zoom);
      
      // Add a simple base layer - Sentinel-2 composite
      const image = ee.ImageCollection('COPERNICUS/S2_SR')
        .filterDate('2023-01-01', '2023-12-31')
        .filterBounds(ee.Geometry.Point([center[1], center[0]]))
        .sort('CLOUD_COVERAGE_ASSESSMENT')
        .first();
      
      // Add the layer based on selected visualization
      switch (layer) {
        case 'rgb':
          map.addLayer(image, {
            bands: ['B4', 'B3', 'B2'],
            min: 0,
            max: 3000,
            gamma: 1.4
          }, 'RGB');
          break;
        case 'ndvi':
          const ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI');
          map.addLayer(ndvi, {
            min: -0.2,
            max: 0.8,
            palette: ['red', 'yellow', 'green']
          }, 'NDVI');
          break;
        case 'nbr':
          const nbr = image.normalizedDifference(['B8', 'B12']).rename('NBR');
          map.addLayer(nbr, {
            min: -1,
            max: 1,
            palette: ['red', 'orange', 'yellow', 'white', 'blue']
          }, 'NBR');
          break;
      }
      
      setLoading(false);
      console.log('Map rendered successfully');
      
    } catch (error) {
      console.error('Error rendering map:', error);
      setError(`Failed to render map: ${error instanceof Error ? error.message : String(error)}`);
      setLoading(false);
    }
  };

  // Update map when layer changes
  useEffect(() => {
    if (mapInitialized) {
      setLoading(true);
      renderMap();
    }
  }, [layer, mapInitialized]);

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
            <p>Loading imagery...</p>
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
      </div>
    </div>
  );
}
