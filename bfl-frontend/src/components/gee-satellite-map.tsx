"use client";

import { useEffect, useRef, useState } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Calendar } from '@/components/ui/calendar';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { format, subDays } from 'date-fns';
import { CalendarIcon, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

// Define props interface
export interface GEESatelliteMapProps {
  className?: string;
  regionId?: string;
  center?: [number, number]; // [lat, lng]
  zoom?: number;
  initialLayer?: 'rgb' | 'ndvi' | 'nbr';
}

export default function GEESatelliteMap({
  className,
  regionId = 'luiz-antonio',
  center = [-21.57, -47.85], // Default to Luiz Antonio coordinates
  zoom = 12,
  initialLayer = 'rgb'
}: GEESatelliteMapProps) {
  const mapRef = useRef<HTMLDivElement>(null);
  const [layer, setLayer] = useState<'rgb' | 'ndvi' | 'nbr'>(initialLayer);
  const [date, setDate] = useState<Date>(new Date());
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [mapInitialized, setMapInitialized] = useState<boolean>(false);
  const [cloudCover, setCloudCover] = useState<number | null>(null);

  // Define ee as any to handle Google Earth Engine API
  // This is necessary because the GEE API is loaded dynamically
  const ee = typeof window !== 'undefined' ? (window as any).ee : undefined;

  // Initialize Google Earth Engine and map
  useEffect(() => {
    // Load Google Earth Engine API script
    const script = document.createElement('script');
    script.src = 'https://earthengine.googleapis.com/v1alpha/bundle.js';
    script.async = true;
    script.onload = initializeEarthEngine;
    document.body.appendChild(script);

    return () => {
      if (document.body.contains(script)) {
        document.body.removeChild(script);
      }
    };
  }, []);

  // Function to initialize Earth Engine with service account
  const initializeEarthEngine = async () => {
    try {
      console.log('Initializing Earth Engine...');
      // Access ee through window to avoid TypeScript errors
      if ((window as any).ee) {
        console.log('Earth Engine API loaded, attempting to initialize...');
        
        // Initialize without authentication for now (public access)
        await (window as any).ee.initialize();
        console.log('Earth Engine initialized successfully');
        setMapInitialized(true);
      } else {
        console.error('Earth Engine API not found in window object');
        throw new Error('Earth Engine API not loaded');
      }
    } catch (error) {
      console.error('Error initializing Earth Engine:', error);
      setError(`Failed to initialize Google Earth Engine: ${error instanceof Error ? error.message : String(error)}`);
      setLoading(false);
    }
  };

  // Update map when layer, date, or initialization status changes
  useEffect(() => {
    if (!mapInitialized || !mapRef.current) {
      console.log('Map not ready yet. Initialized:', mapInitialized, 'Ref exists:', !!mapRef.current);
      return;
    }

    const updateMap = async () => {
      try {
        console.log('Updating map with layer:', layer, 'date:', date);
        setLoading(true);
        setError(null);

        // Access Earth Engine API through window
        const ee = (window as any).ee;
        if (!ee) {
          throw new Error('Earth Engine API not available');
        }

        console.log('Creating map instance...');
        const map = new ee.Map(mapRef.current);
        
        // Set map center and zoom
        map.setCenter(center[1], center[0], zoom);
        console.log('Map centered at:', center, 'with zoom:', zoom);

        // Format date for Earth Engine
        const dateString = format(date, 'yyyy-MM-dd');
        
        // Find least cloudy Sentinel-2 image within 10 days before the selected date
        const startDate = format(subDays(date, 10), 'yyyy-MM-dd');
        console.log('Searching for images between', startDate, 'and', dateString);
        
        console.log('Creating image collection...');
        const sentinel2 = ee.ImageCollection('COPERNICUS/S2_SR')
          .filterDate(startDate, dateString)
          .filterBounds(ee.Geometry.Point([center[1], center[0]]))
          .sort('CLOUDY_PIXEL_PERCENTAGE');
        
        // Get the least cloudy image
        console.log('Getting first (least cloudy) image...');
        const image = sentinel2.first();
        
        // Check if we have an image
        console.log('Checking if image exists...');
        image.bandNames().evaluate((bandNames: any) => {
          if (!bandNames || bandNames.length === 0) {
            console.error('No image found for the selected date range');
            setError('No satellite imagery found for the selected date range');
            setLoading(false);
            return;
          }
          console.log('Image found with bands:', bandNames);
          
          // Get cloud cover percentage
          image.get('CLOUDY_PIXEL_PERCENTAGE').evaluate((cloudiness: number) => {
            console.log('Cloud cover:', cloudiness);
            setCloudCover(cloudiness);
          });
        });
        
        // Create visualization based on selected layer
        console.log('Creating visualization for layer:', layer);
        let visParams;
        switch (layer) {
          case 'rgb':
            // True color RGB visualization
            visParams = {
              bands: ['B4', 'B3', 'B2'],
              min: 0,
              max: 3000,
              gamma: 1.4
            };
            console.log('Adding RGB layer with params:', visParams);
            map.addLayer(image, visParams, 'Sentinel-2');
            break;
          case 'ndvi':
            // Calculate NDVI
            console.log('Calculating NDVI...');
            const ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI');
            visParams = {
              bands: ['NDVI'],
              min: -0.2,
              max: 0.8,
              palette: [
                'FFFFFF', 'CE7E45', 'DF923D', 'F1B555', 'FCD163', '99B718',
                '74A901', '66A000', '529400', '3E8601', '207401', '056201',
                '004C00', '023B01', '012E01', '011D01', '011301'
              ]
            };
            console.log('Adding NDVI layer with params:', visParams);
            map.addLayer(ndvi, visParams, 'NDVI');
            break;
          case 'nbr':
            // Calculate NBR (Normalized Burn Ratio)
            console.log('Calculating NBR...');
            const nbr = image.normalizedDifference(['B8', 'B12']).rename('NBR');
            visParams = {
              bands: ['NBR'],
              min: -1.0,
              max: 1.0,
              palette: [
                '7a0000', 'b60000', 'e60000', 'ff2b2b', 'ff5555', 'ff8080',
                'ffaaaa', 'ffd5d5', 'ffffff', 'd5d5ff', 'aaaaff', '8080ff',
                '5555ff', '2b2bff', '0000e6', '0000b6', '00007a'
              ]
            };
            console.log('Adding NBR layer with params:', visParams);
            map.addLayer(nbr, visParams, 'NBR');
            break;
        }
        
        console.log('Map updated successfully');
        setLoading(false);
      } catch (error) {
        console.error('Error updating map:', error);
        setError(`Failed to load satellite imagery: ${error instanceof Error ? error.message : String(error)}`);
        setLoading(false);
      }
    };

    updateMap();
  }, [mapInitialized, layer, date, center, zoom]);

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
        
        <div className="flex items-center gap-2">
          <Popover>
            <PopoverTrigger asChild>
              <Button
                variant="outline"
                className={cn(
                  "w-[240px] justify-start text-left font-normal",
                  !date && "text-muted-foreground"
                )}
              >
                <CalendarIcon className="mr-2 h-4 w-4" />
                {date ? format(date, "PPP") : <span>Pick a date</span>}
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-auto p-0" align="end">
              <Calendar
                mode="single"
                selected={date}
                onSelect={(newDate) => newDate && setDate(newDate)}
                disabled={(date) => date > new Date() || date < new Date('2017-01-01')}
                initialFocus
              />
            </PopoverContent>
          </Popover>
          
          {cloudCover !== null && (
            <Badge variant="outline">
              Cloud cover: {cloudCover.toFixed(1)}%
            </Badge>
          )}
        </div>
      </div>
    </div>
  );
}
