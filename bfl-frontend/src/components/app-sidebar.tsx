"use client"

import React, { useState, useEffect } from "react"
import { Map } from "lucide-react"

import Link from "next/link"
import {
  Sidebar,
  SidebarContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar"

// Dynamic regions fetched from backend
interface Region { areaId: string; name: string }

export function AppSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
  const [regions, setRegions] = useState<Region[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  
  useEffect(() => {
    // Temporarily hardcode regions to only show Brazil Rondonia
    const hardcodedRegions = [
      { areaId: "brazil-rondonia", name: "Brazil Rondonia" }
    ];
    setRegions(hardcodedRegions);
    setIsLoading(false);
    setError(null);
    // Original fetchRegions logic commented out for now:
    /*
    const fetchRegions = async () => {
      setIsLoading(true)
      setError(null)
      try {
        const bucketName = "bfl-satellite-imagery-339712843779";
        const s3Url = `https://${bucketName}.s3.amazonaws.com/?list-type=2&delimiter=/`;

        const response = await fetch(s3Url);

        if (!response.ok) {
          throw new Error(`S3 API error: ${response.status} ${response.statusText}. Check bucket permissions and CORS policy.`);
        }

        const xmlText = await response.text();
        const parser = new DOMParser();
        const xmlDoc = parser.parseFromString(xmlText, "application/xml");

        const errorNode = xmlDoc.querySelector("Error");
        if (errorNode) {
          const errorCode = errorNode.querySelector("Code")?.textContent;
          const errorMessage = errorNode.querySelector("Message")?.textContent;
          throw new Error(`S3 Error: ${errorCode} - ${errorMessage}`);
        }

        const commonPrefixes = Array.from(xmlDoc.querySelectorAll("CommonPrefixes Prefix"));
        const fetchedRegions = commonPrefixes.map(prefixNode => {
          const fullPath = prefixNode.textContent || "";
          const areaId = fullPath.replace(/\/$/, "");
          const name = areaId.split('-').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' '); 
          return { areaId, name };
        });

        if (fetchedRegions.length === 0) {
          console.warn("No common prefixes (folders) found in S3 bucket or unable to parse them.");
        }
        setRegions(fetchedRegions);

      } catch (err) {
        console.error('Failed to fetch regions from S3:', err);
        setError(err instanceof Error ? err.message : 'An unknown error occurred while fetching S3 locations. Check console for details and ensure S3 bucket CORS policy is correctly configured for this domain.');
        setRegions([]);
      } finally {
        setIsLoading(false);
      }
    };
    
    fetchRegions()
    */
  }, [])

  return (
    <Sidebar variant="inset" {...props}>
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" asChild>
              <Link href="/">
                <div className="bg-sidebar-primary text-sidebar-primary-foreground flex aspect-square size-8 items-center justify-center rounded-lg">
                  <Map className="size-4" />
                </div>
                <div className="grid flex-1 text-left text-sm leading-tight">
                  <span className="truncate font-medium">Brazil Flying Labs</span>
                  <span className="truncate text-xs"></span>
                </div>
              </Link>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>
      <SidebarContent>
        <div className="px-4 py-2">
          <h2 className="text-sm text-sidebar-primary-foreground font-semibold">Satellite Analysis Dashboard</h2>
          <p className="text-xs text-sidebar-primary-foreground mt-1">Monitor fire damage and recovery across Brazil</p>
        </div>
        
        <div className="px-4 py-2">
          <h3 className="text-xs text-sidebar-primary-foreground font-medium mb-2">SELECT REGION</h3>
          <div className="space-y-1">
            {isLoading ? (
              <div className="text-xs text-sidebar-primary-foreground/70 px-2 py-1.5">
                Loading regions...
              </div>
            ) : error ? (
              <div className="text-xs text-red-500 px-2 py-1.5">
                Error: {error}
              </div>
            ) : regions.length === 0 ? (
              <div className="text-xs text-sidebar-primary-foreground/70 px-2 py-1.5">
                No regions available
              </div>
            ) : (
              regions.map(region => (
                <Link
                  key={region.areaId}
                  href={`/dashboard?region=${region.areaId}`}
                  className="flex items-center gap-2 px-2 py-1.5 text-sm rounded-md hover:bg-muted transition-colors"
                >
                  <Map className="h-4 w-4 text-sidebar-primary-foreground" />
                  <span>{region.name}</span>
                </Link>
              ))
            )}
          </div>
        </div>
        
        <div className="px-4 py-2 mt-4">
          <h3 className="text-xs text-sidebar-primary-foreground font-medium mb-2">ABOUT</h3>
          <div className="text-xs text-sidebar-primary-foreground space-y-2">
            <p>This dashboard provides satellite imagery analysis of burn detection and recovery monitoring across protected areas in Brazil.</p>
            <p>Data is sourced from Sentinel-2 satellite imagery and processed using Google Earth Engine.</p>
          </div>
        </div>
      </SidebarContent>
    </Sidebar>
  )
}
