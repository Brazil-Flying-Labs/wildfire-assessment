'use client'

import { useState, useEffect } from 'react'
import dynamic from 'next/dynamic'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Map } from "lucide-react"
import type { LatLngTuple } from 'leaflet'

// Dynamically import Leaflet components to avoid SSR issues
const MapContainer = dynamic(
  () => import('react-leaflet').then((mod) => mod.MapContainer),
  { ssr: false }
)

const TileLayer = dynamic(
  () => import('react-leaflet').then((mod) => mod.TileLayer),
  { ssr: false }
)

// Luiz Antonio coordinates (approximate)
const STATION_CENTER: LatLngTuple = [-21.61, -47.77]
const DEFAULT_ZOOM = 12

// Example geometry for the Luiz Antonio station area
const stationGeometry = {
  type: 'Polygon',
  coordinates: [[
    [-47.79, -21.62],
    [-47.76, -21.62],
    [-47.76, -21.60],
    [-47.79, -21.60],
    [-47.79, -21.62]
  ]]
}

export function StationMap() {
  const [tileUrl, setTileUrl] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [mapReady, setMapReady] = useState(false)

  // This effect ensures we only render the map on the client side
  useEffect(() => {
    setMapReady(true)
  }, [])

  // Request body for the burn severity API
  const requestBody = {
    geometry: stationGeometry,
    preFireYears: [2020, 2021],
    preStartMMDD: '-07-01',
    preEndMMDD: '-10-15',
    postFireYear: 2024,
    postStartMMDD: '-08-01',
    postEndMMDD: '-10-15'
  }

  async function fetchBurnSeverity() {
    setIsLoading(true)
    try {
      const resp = await fetch('/api/burnSeverity', {
        method: 'POST',
        body: JSON.stringify(requestBody)
      })
      const data = await resp.json()
      if (data.tileUrl) {
        setTileUrl(data.tileUrl)
      } else {
        console.error('No tileUrl returned:', data)
      }
    } catch (error) {
      console.error('Error fetching burn severity data:', error)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <Card className="h-full">
      <CardHeader>
        <CardTitle>Station Map</CardTitle>
        <CardDescription>Luiz Antônio Ecological Station</CardDescription>
      </CardHeader>
      <CardContent className="p-0 overflow-hidden">
        {mapReady ? (
          <div className="relative">
            <div className="absolute top-4 right-4 z-10">
              <Button 
                onClick={fetchBurnSeverity} 
                disabled={isLoading} 
                size="sm" 
                variant="secondary"
                className="shadow-md"
              >
                {isLoading ? 'Loading...' : 'Show Burn Severity'}
              </Button>
            </div>
            <MapContainer 
              center={STATION_CENTER}
              zoom={DEFAULT_ZOOM} 
              style={{ height: '400px', width: '100%' }}
              className="z-0"
            >
              {/* Base map layer */}
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />
              
              {/* Burn severity overlay (conditionally rendered) */}
              {tileUrl && <TileLayer url={tileUrl} />}
            </MapContainer>
            
            <div className="grid grid-cols-2 gap-4 text-sm p-4">
              <div className="flex items-center gap-2">
                <div className="size-3 rounded-full bg-green-500"></div>
                <span>Intact Forest</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="size-3 rounded-full bg-red-500"></div>
                <span>Fire-Affected</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="size-3 rounded-full bg-blue-500"></div>
                <span>Water Bodies</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="size-3 rounded-full bg-amber-500"></div>
                <span>Research Zones</span>
              </div>
            </div>
          </div>
        ) : (
          <div className="aspect-video bg-muted rounded-md flex items-center justify-center">
            <div className="text-center">
              <Map className="size-10 mx-auto text-muted-foreground" />
              <p className="text-sm text-muted-foreground mt-2">Loading map...</p>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
