"use client"

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { 
  Card, 
  CardContent, 
  CardHeader, 
  CardTitle 
} from '@/components/ui/card'
import { 
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion'
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/label'
import { Layers, Info } from 'lucide-react'
import { 
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { Slider } from '@/components/ui/slider'

export interface LayerOption {
  id: string
  name: string
  description: string
  enabled: boolean
}

export interface LayerControlsProps {
  className?: string
  onChange?: (layers: LayerOption[]) => void
}

export function LayerControls({
  className,
  onChange
}: LayerControlsProps) {
  // Initial layer options based on the meeting transcript
  const [layers, setLayers] = useState<LayerOption[]>([
    {
      id: 'rgb',
      name: 'RGB (Visual)',
      description: 'Standard visual imagery from satellite',
      enabled: true
    },
    {
      id: 'ndvi',
      name: 'NDVI (Vegetation Index)',
      description: 'Normalized Difference Vegetation Index - measures vegetation health',
      enabled: false
    },
    {
      id: 'nbr',
      name: 'NBR (Burn Ratio)',
      description: 'Normalized Burn Ratio - highlights burned areas',
      enabled: false
    },
    {
      id: 'mask',
      name: 'Soil Mask',
      description: 'Mask of exposed soil areas (excluded from analysis)',
      enabled: false
    }
  ])
  
  // Filter controls
  const [burnSeverityThreshold, setBurnSeverityThreshold] = useState<number>(0.1)
  const [cloudCoverage, setCloudCoverage] = useState<number>(30) // Default from transcript
  
  // Handle layer toggle
  const handleLayerToggle = (layerId: string, enabled: boolean) => {
    const updatedLayers = layers.map(layer => 
      layer.id === layerId ? { ...layer, enabled } : layer
    )
    setLayers(updatedLayers)
    
    if (onChange) {
      onChange(updatedLayers)
    }
  }

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Layers className="h-5 w-5" />
            <span>Layer Controls</span>
          </CardTitle>
        </div>
      </CardHeader>
      <CardContent>
        <Accordion type="single" collapsible defaultValue="layers">
          <AccordionItem value="layers">
            <AccordionTrigger>Image Layers</AccordionTrigger>
            <AccordionContent>
              <div className="space-y-4">
                {layers.map(layer => (
                  <div key={layer.id} className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Switch 
                        id={`layer-${layer.id}`}
                        checked={layer.enabled}
                        onCheckedChange={(checked: boolean) => handleLayerToggle(layer.id, checked)}
                      />
                      <Label htmlFor={`layer-${layer.id}`}>{layer.name}</Label>
                    </div>
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <Button variant="ghost" size="icon" className="h-6 w-6">
                            <Info className="h-4 w-4" />
                          </Button>
                        </TooltipTrigger>
                        <TooltipContent>
                          <p className="max-w-xs">{layer.description}</p>
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                  </div>
                ))}
              </div>
            </AccordionContent>
          </AccordionItem>
          
          <AccordionItem value="filters">
            <AccordionTrigger>Analysis Filters</AccordionTrigger>
            <AccordionContent>
              <div className="space-y-6">
                <div className="space-y-2">
                  <Label htmlFor="burn-severity">
                    Burn Severity Threshold: {burnSeverityThreshold.toFixed(2)}
                  </Label>
                  <Slider 
                    id="burn-severity"
                    min={0} 
                    max={1} 
                    step={0.01} 
                    value={[burnSeverityThreshold]}
                    onValueChange={(value: number[]) => setBurnSeverityThreshold(value[0])}
                  />
                  <p className="text-xs text-muted-foreground">
                    Higher values show only more severely burned areas
                  </p>
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="cloud-coverage">
                    Max Cloud Coverage: {cloudCoverage}%
                  </Label>
                  <Slider 
                    id="cloud-coverage"
                    min={0} 
                    max={100} 
                    step={5} 
                    value={[cloudCoverage]}
                    onValueChange={(value: number[]) => setCloudCoverage(value[0])}
                  />
                  <p className="text-xs text-muted-foreground">
                    Filter satellite imagery by maximum cloud coverage
                  </p>
                </div>
              </div>
            </AccordionContent>
          </AccordionItem>
        </Accordion>
      </CardContent>
    </Card>
  )
}
