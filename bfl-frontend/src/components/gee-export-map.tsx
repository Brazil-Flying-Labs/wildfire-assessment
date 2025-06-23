"use client";

import { useEffect, useRef, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Calendar } from '@/components/ui/calendar';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { format, subDays } from 'date-fns';
import { CalendarIcon, Loader2, RefreshCw } from 'lucide-react';
import { cn } from '@/lib/utils';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// Define props interface
export interface GEEExportMapProps {
  className?: string;
  regionId?: string;
  center?: [number, number]; // [lat, lng]
  zoom?: number;
  initialLayer?: 'rgb' | 'ndvi' | 'nbr';
}

export default function GEEExportMap({
  className,
  regionId = 'luiz-antonio',
  center = [-21.57, -47.85], // Default to Luiz Antonio coordinates
  zoom = 12,
  initialLayer = 'rgb'
}: GEEExportMapProps) {
  const mapRef = useRef<HTMLDivElement>(null);
  const leafletMapRef = useRef<L.Map | null>(null);
  const [layer, setLayer] = useState<'rgb' | 'ndvi' | 'nbr'>(initialLayer);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [date, setDate] = useState<Date>(new Date());
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [exportStatus, setExportStatus] = useState<string>('idle');
  const imageLayerRef = useRef<L.ImageOverlay | null>(null);

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
      
      // Request initial imagery
      requestEarthEngineExport();
      
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
  
  // Request Earth Engine export when layer or date changes
  useEffect(() => {
    if (leafletMapRef.current) {
      requestEarthEngineExport();
    }
  }, [layer, date]);
  
  // State for detailed error information
  const [detailedError, setDetailedError] = useState<any>(null);
  const [cloudCover, setCloudCover] = useState<number | null>(null);

  // Function to request Earth Engine export
  const requestEarthEngineExport = async () => {
    if (!leafletMapRef.current) return;
    
    try {
      setLoading(true);
      setExportStatus('exporting');
      setError(null);
      setDetailedError(null);
      
      // Remove existing image overlay
      if (imageLayerRef.current && leafletMapRef.current) {
        leafletMapRef.current.removeLayer(imageLayerRef.current);
        imageLayerRef.current = null;
      }
      
      // Format dates for the API request
      const startDate = format(subDays(date, 5), 'yyyy-MM-dd');
      const endDate = format(date, 'yyyy-MM-dd');
      
      console.log(`Requesting ${layer} export for date range: ${startDate} to ${endDate}`);
      
      // Make API request to our GEE Export endpoint
      const response = await fetch('/api/gee-export', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          region: regionId,
          startDate,
          endDate,
          layer,
          center,
          zoom
        }),
      });
      
      const data = await response.json();
      console.log('Export response:', data);
      
      if (!response.ok) {
        // Store detailed error information for debugging
        setDetailedError(data);
        
        // Create a user-friendly error message
        let errorMessage = 'Export failed';
        if (data.error) {
          errorMessage += `: ${data.error}`;
          
          // Add more specific messages for common errors
          if (data.error.includes('No images found')) {
            errorMessage = `No satellite images found for the selected date range (${startDate} to ${endDate}). Please try a different date.`;
          } else if (data.error.includes('service account')) {
            errorMessage = 'Authentication error with Google Earth Engine. Please check your service account credentials.';
          } else if (data.error.includes('timeout')) {
            errorMessage = 'The export operation timed out. Please try again or select a smaller region.';
          }
        }
        
        throw new Error(errorMessage);
      }
      
      if (data.success && data.imageUrl) {
        setImageUrl(data.imageUrl);
        setExportStatus('completed');
        
        // Set cloud cover if available
        if (data.cloudCover !== undefined) {
          setCloudCover(data.cloudCover);
        }
        
        // In a real implementation, we would add the image overlay to the map
        // For now, we'll add a marker to indicate success
        if (leafletMapRef.current) {
          const cloudInfo = data.cloudCover !== undefined ? 
            `<br>Cloud coverage: ${data.cloudCover.toFixed(2)}%` : '';
            
          L.marker(center).addTo(leafletMapRef.current)
            .bindPopup(`${layer.toUpperCase()} export completed.<br>Date range: ${startDate} to ${endDate}${cloudInfo}`)
            .openPopup();
        }
      } else {
        throw new Error('Export did not return a valid image URL');
      }
      
    } catch (err) {
      console.error('Error requesting Earth Engine export:', err);
      setError(`${err instanceof Error ? err.message : String(err)}`);
      setExportStatus('failed');
    } finally {
      setLoading(false);
    }
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
            <p>Exporting imagery from Earth Engine...</p>
          </div>
        </div>
      )}
      
      {/* Error message */}
      {error && (
        <div className="absolute inset-0 flex items-center justify-center bg-black bg-opacity-30 z-10">
          <div className="bg-white p-6 rounded-md shadow-md max-w-md">
            <h3 className="text-lg font-medium mb-2">Error</h3>
            <p className="text-red-500 mb-4">{error}</p>
            
            {detailedError && (
              <div className="mt-2 mb-4">
                <details className="text-xs">
                  <summary className="text-sm text-gray-600 cursor-pointer hover:text-gray-800">
                    Technical details
                  </summary>
                  <div className="mt-2 p-2 bg-gray-50 rounded border border-gray-200 overflow-auto max-h-40">
                    <pre className="whitespace-pre-wrap">
                      {detailedError.stackTrace || JSON.stringify(detailedError, null, 2)}
                    </pre>
                  </div>
                </details>
              </div>
            )}
            
            <div className="flex justify-between items-center mt-4">
              <p className="text-xs text-gray-500">Check browser console for more details</p>
              <Button 
                onClick={() => requestEarthEngineExport()} 
                variant="outline"
                size="sm"
              >
                <RefreshCw className="mr-2 h-4 w-4" />
                Retry
              </Button>
            </div>
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
              <Button variant="outline" className="w-[240px] justify-start text-left font-normal">
                <CalendarIcon className="mr-2 h-4 w-4" />
                {format(date, 'PPP')}
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
          
          {exportStatus === 'completed' && (
            <Badge variant="outline" className="px-2 py-1 bg-green-50">
              Export complete
            </Badge>
          )}
          
          {exportStatus === 'failed' && (
            <Badge variant="outline" className="px-2 py-1 bg-red-50 text-red-500">
              Export failed
            </Badge>
          )}
        </div>
      </div>
    </div>
  );
}
