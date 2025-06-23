"use client"

import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { 
  Card, 
  CardContent, 
  CardHeader, 
  CardTitle,
  CardDescription
} from '@/components/ui/card'
import { Download, FileType2, FileImage, Package, Loader2 } from 'lucide-react'
import { Checkbox } from '@/components/ui/checkbox'
import { Label } from '@/components/ui/label'
import { cn } from '@/lib/utils'

export interface DownloadOption {
  id: string
  name: string
  description: string
  fileType: string
  fileSize: string
  selected: boolean
}

export interface DataDownloadProps {
  className?: string
  regionId: string
  fromDate?: Date
  toDate?: Date
}

export function DataDownload({
  className,
  regionId,
  fromDate,
  toDate
}: DataDownloadProps) {
  const [downloadOptions, setDownloadOptions] = useState<DownloadOption[]>([
    {
      id: 'rgb',
      name: 'RGB Imagery',
      description: 'Full resolution visual satellite imagery',
      fileType: 'GeoTIFF',
      fileSize: '250 MB',
      selected: true
    },
    {
      id: 'ndvi',
      name: 'NDVI Data',
      description: 'Normalized Difference Vegetation Index data',
      fileType: 'GeoTIFF',
      fileSize: '125 MB',
      selected: false
    },
    {
      id: 'nbr',
      name: 'NBR Data',
      description: 'Normalized Burn Ratio data',
      fileType: 'GeoTIFF',
      fileSize: '125 MB',
      selected: false
    },
    {
      id: 'mask',
      name: 'Soil Mask',
      description: 'Mask of exposed soil areas',
      fileType: 'GeoTIFF',
      fileSize: '30 MB',
      selected: false
    },
    {
      id: 'statistics',
      name: 'Analysis Statistics',
      description: 'CSV containing burn area statistics',
      fileType: 'CSV',
      fileSize: '2 MB',
      selected: false
    }
  ])
  
  const [downloadFormat, setDownloadFormat] = useState<'individual' | 'package'>('individual')
  const [isDownloading, setIsDownloading] = useState(false)
  const [links, setLinks] = useState<{ id: string; date: string; url: string }[]>([])

  // Fetch signed URLs for each selected option and date
  useEffect(() => {
    if (!regionId || !fromDate || !toDate) return
    const dates = [fromDate, toDate]
    const selected = downloadOptions.filter(o => o.selected).map(o => o.id)
    Promise.all(
      dates.flatMap(date => {
        const dateStr = date.toISOString().split('T')[0]
        return selected.map(id =>
          fetch(`${process.env.NEXT_PUBLIC_API_BASE}/images?areaId=${regionId}&date=${dateStr}&type=${id}`)
            .then(res => res.json())
            .then(data => ({ id, date: dateStr, url: data.url }))
        )
      })
    ).then(setLinks).catch(console.error)
  }, [regionId, fromDate, toDate, downloadOptions])

  // Toggle selection for download option
  const toggleOption = (id: string) => {
    setDownloadOptions(downloadOptions.map(option => 
      option.id === id ? { ...option, selected: !option.selected } : option
    ))
  }
  
  // Calculate total download size
  const totalSize = downloadOptions
    .filter(option => option.selected)
    .reduce((total, option) => {
      const size = parseInt(option.fileSize.replace(' MB', ''))
      return total + size
    }, 0)
  
  // Mock download function
  const handleDownload = () => {
    setIsDownloading(true)
    
    // Simulate download delay
    setTimeout(() => {
      // Trigger downloads
      links.forEach(link => {
        const a = document.createElement('a')
        a.href = link.url
        a.download = `${link.id}_${link.date}`
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
      })
      setIsDownloading(false)
    }, 2000)
  }
  
  // Get icon based on file type
  const getFileIcon = (fileType: string) => {
    switch(fileType) {
      case 'GeoTIFF':
        return <FileImage className="h-4 w-4" />
      case 'CSV':
        return <FileType2 className="h-4 w-4" />
      default:
        return <FileType2 className="h-4 w-4" />
    }
  }

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Download className="h-5 w-5" />
          <span>Download Data</span>
        </CardTitle>
        <CardDescription>
          Download processed satellite data for further analysis in GIS software
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <div className="flex justify-between text-sm">
            <span>Selected time period:</span>
            <span className="font-medium">
              {fromDate && toDate 
                ? `${fromDate.toLocaleDateString()} - ${toDate.toLocaleDateString()}` 
                : 'No period selected'}
            </span>
          </div>
          
          <div className="space-y-2">
            <div className="text-sm font-medium">Download Format</div>
            <div className="flex space-x-4">
              <div className="flex items-center space-x-2">
                <input
                  type="radio"
                  id="format-individual"
                  checked={downloadFormat === 'individual'}
                  onChange={() => setDownloadFormat('individual')}
                />
                <Label htmlFor="format-individual">Individual Files</Label>
              </div>
              <div className="flex items-center space-x-2">
                <input
                  type="radio"
                  id="format-package"
                  checked={downloadFormat === 'package'}
                  onChange={() => setDownloadFormat('package')}
                />
                <Label htmlFor="format-package">Zip Package</Label>
              </div>
            </div>
          </div>
          
          <div className="space-y-2">
            <div className="text-sm font-medium">Available Files</div>
            <div className="border rounded-md divide-y">
              {downloadOptions.map(option => (
                <div 
                  key={option.id} 
                  className="flex items-center justify-between p-3"
                >
                  <div className="flex items-center gap-3">
                    <Checkbox 
                      id={`download-${option.id}`}
                      checked={option.selected}
                      onCheckedChange={() => toggleOption(option.id)}
                    />
                    <div>
                      <Label 
                        htmlFor={`download-${option.id}`}
                        className="font-medium"
                      >
                        {option.name}
                      </Label>
                      <p className="text-xs text-muted-foreground">{option.description}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    {getFileIcon(option.fileType)}
                    <span>{option.fileType}</span>
                    <span>{option.fileSize}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
          
          <div className="flex items-center justify-between pt-2">
            <div className="text-sm">
              Total size: <span className="font-medium">{totalSize} MB</span>
            </div>
            <Button 
              onClick={handleDownload} 
              disabled={isDownloading || totalSize === 0 || !fromDate || !toDate}
            >
              {isDownloading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Downloading...
                </>
              ) : downloadFormat === 'package' ? (
                <>
                  <Package className="mr-2 h-4 w-4" />
                  Download as Zip
                </>
              ) : (
                <>
                  <Download className="mr-2 h-4 w-4" />
                  Download Files
                </>
              )}
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
