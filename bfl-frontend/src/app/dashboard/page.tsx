"use client"

import { AppSidebar } from "@/components/app-sidebar";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"
import { Separator } from "@/components/ui/separator"
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { AlertTriangle, Flame, Leaf, Droplet, TrendingUp, Map, Calendar, Download, RefreshCw } from "lucide-react"
import { Button } from "@/components/ui/button"
// If the select component doesn't exist, we need to create it or use an alternative
import dynamic from "next/dynamic"
// Import SatelliteMap components with dynamic import to avoid SSR issues
const SatelliteMap = dynamic(() => import("@/components/satellite-map-wrapper"), { ssr: false })

import { TimeComparisonControls } from "@/components/time-comparison-controls"
import { LayerControls } from "@/components/layer-controls"
import { DataDownload } from "@/components/data-download"
import { useState, useEffect } from "react"
import { useSearchParams } from 'next/navigation'
import type { LayerOption } from "@/components/layer-controls"
import { format } from 'date-fns'

export default function Page() {
  const [fromDate, setFromDate] = useState<Date>()
  const [toDate, setToDate] = useState<Date>()
  const searchParams = useSearchParams()
  // Default to first region if no query param
  const regionId = 'brazil-rondonia'; // Temporarily hardcoded for satellite image testing
  const [metrics, setMetrics] = useState<{ totalArea: number; fireAffected: number; recoveryProgress: number } | null>(null)
  const [severityData, setSeverityData] = useState<{ high: number; moderate: number; low: number } | null>(null)
  const [recoveryData, setRecoveryData] = useState<{ timeline: { date: string; value: number }[] } | null>(null)
  const [overviewImageUrl, setOverviewImageUrl] = useState<string | null>(null)
  const [isOverviewImageLoading, setIsOverviewImageLoading] = useState<boolean>(true)
  const [overviewImageError, setOverviewImageError] = useState<string | null>(null)

  // Satellite Tab Specific State
  interface SatelliteImageUrls {
    rgb?: string;
    ndvi?: string;
    nbr?: string;
  }
  const [satelliteImageUrls, setSatelliteImageUrls] = useState<SatelliteImageUrls>({});
  const [isSatelliteImagesLoading, setIsSatelliteImagesLoading] = useState<boolean>(false);
  const [satelliteImagesError, setSatelliteImagesError] = useState<string | null>(null);
  const [selectedSatelliteProductType, setSelectedSatelliteProductType] = useState<keyof SatelliteImageUrls>('rgb');
  // const [enabledLayers, setEnabledLayers] = useState<string[]>(['rgb']) // No longer directly used for this new switcher

  // Common state for date selection
  const [availableDates, setAvailableDates] = useState<string[]>(['2023-01-15']) // Hardcoded for now
  const [selectedDate, setSelectedDate] = useState<string>('2023-01-15') // Default to the only available date
  const [baselineDate, setBaselineDate] = useState<string | undefined>(undefined)

  // Legacy state, review if still needed or can be merged/removed
  const [isLoading, setIsLoading] = useState(false) // Generic loading, might be redundant
  const [imageUrls, setImageUrls] = useState<Record<string, Record<string, string>>>({}) // Potentially replaced by satelliteImageUrls
  const [diffUrls, setDiffUrls] = useState<{ ndvi1: string; ndvi2: string } | null>(null)
  const [bflProducts, setBflProducts] = useState<Record<string, string>>({}) // Potentially replaced by satelliteImageUrls
  const [isBflLoading, setIsBflLoading] = useState(false); // Potentially replaced by isSatelliteImagesLoading
  const [bflError, setBflError] = useState<string | null>(null); // Potentially replaced by satelliteImagesError

  // TiTiler URLs from CloudFormation outputs
  // Use the new API and CDN URLs from environment variables
  const tiTilerApiUrl = process.env.NEXT_PUBLIC_API_BASE || 'https://y7s6nh2e24.execute-api.us-east-1.amazonaws.com/v1/';
  const tiTilerCdnUrl = process.env.NEXT_PUBLIC_CDN || 'https://d3nl71iv3sr2rn.cloudfront.net';
  const s3BucketName = process.env.NEXT_PUBLIC_S3_BUCKET || 'bfl-satellite-imagery-339712843779';
  const apiBase = process.env.NEXT_PUBLIC_API_BASE || '';
  const cdnUrl = process.env.NEXT_PUBLIC_CDN || 'https://cdn.staclint.com';

  // Effect to set available dates (hardcoded for now)
  useEffect(() => {
    setAvailableDates(['2023-01-15']);
    setSelectedDate('2023-01-15');
  }, []); // Run once on mount

  useEffect(() => {
    if (!regionId) return
    fetch(`${process.env.NEXT_PUBLIC_API_BASE}/images?areaId=${regionId}`)
      .then(res => res.json())
      .then(data => {
        // sort ISO date strings chronologically
        const sorted = data.timestamps.sort((a: string, b: string) => a.localeCompare(b));
        setAvailableDates(sorted);
      })
      .catch(err => console.error('Failed to list dates:', err))
  }, [regionId])

  useEffect(() => {
    if (availableDates.length && !fromDate && !toDate) {
      const lastTs = availableDates[availableDates.length - 1]
      const dt = new Date(lastTs)
      setFromDate(dt)
      setToDate(dt)
    }
  }, [availableDates, fromDate, toDate])

  useEffect(() => {
    const bucketName = s3BucketName; // Use the s3BucketName defined earlier in the component
    if (!regionId || !bucketName) {
      setOverviewImageError("Region ID or S3 bucket name is not configured.");
      setIsOverviewImageLoading(false);
      setOverviewImageUrl(null);
      return;
    }

    // Temporarily hardcode the overview image to the provided pre-signed S3 URL
    const presignedImageUrl = "https://bfl-satellite-imagery-339712843779.s3.us-east-1.amazonaws.com/brazil-rondonia/2023-01-15/RGB.png?response-content-disposition=inline&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEHIaCXVzLWVhc3QtMSJHMEUCICRanIl8cHpk1Nll6D0%2BOGWFDA0vG1VO%2By3JP7hHKdVMAiEA2Q%2F3q7vji0D3WFc3MvoB3E9%2BxgOsZMa%2FiIzwmMItl%2BsqzAMISxAAGgwzMzk3MTI4NDM3NzkiDAOwwCon93I17%2BHgZyqpAzmdAGtjIElFT6HmR84moKaRnQ61tRkPoix7bmig792eI7r81z3cpxnxAG%2BFvGzF2HAA%2BVB%2FpnpCQyr%2F5HYebM%2FfFzTf5y8F5zIcv%2B710746NfG67Qat6MF7XM5vPP0jri3TRBIWzdceD0BufdESnWhjtFiYGVJVS5Ws2naSJF6GwhqwlWWaApDPg%2FbwNgXHuGUlW8BBWFkRJEhyzxqhBo0iVi7IsGCRCXAX2tpI4HUAQ9VDJxhfmECbQJySfxnNIcD2%2FFfYv62HyPj%2Fw1Xv21KhvZYCzHdV9VS7sQPRTwEu7TT6eQfpVXKkcfCiIJUpPsAVRPzCkbVAsgF4zlhn9d1HbByb%2FrfuTNMI5G0DOgYdHqBKOKOFOm6FT48vm4M25MvN0ZZhD%2FlOSfBCUWiCH%2FDDOR%2BpfYpD8El8wjdnYVDQlPjg7sWcpPwSZtpbMOqH1m8G8bAIXAS1L1scvXTksdB86MFlh8RTE0%2BQbQF0SC5Kr0CJsZKm6x62kPetqA2POm9N2iTMVF8fyuE0oWCDkc98CRxI2XIUnR8b5%2BDKs2TG6bDiDEExmPbyMIrZhsIGOt4CtKgKX%2FcbEYWKuhPGzqPi1mcCANYReezxBFTPWrXjbVq2fbAJ%2BfPYo7hhaBlW1Tj2gR2T6UP3RLLMgn7ALzZXSNXutOItUbmeGyttG%2FfoMrEIvlsVIxDcN7kIZpfMAkpEzalmADjdgEk3QOG%2Fp8sYRSf969iSp9LTCkyVqo63eFbGd10D9nM8aXBoVqDf6havz1b5RZV6SAdqa1ScP0hfkQzpxjbxjmVM22yt4aQWJpSBluQfvLtEYP2zOnEhJeVWzd6SMlecxusshub%2F5WgvBtnhKWI5BqEwMasFB%2FP68vnlXlujRPlwg1MUXmArtNM9oW4UYm6RZP%2Fdvn6UvpVeCcGLMWepjPbrO6wflyD%2BjgG2a0AmxO9WXKuVogFSybhWrEwI9%2BBe5nckkQUnDVU8aGKYrpHKrQx4rOTmK8XEQUNLlHwSA6QAiMOvycm2VizoJxyNqM87QgWw5JLN59Y%3D&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=ASIAU6GDWUAB3OBLAASR%2F20250605%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Date=20250605T174533Z&X-Amz-Expires=43200&X-Amz-SignedHeaders=host&X-Amz-Signature=19866cde7bef648f8272a9119508ab7354ebc8d66359cfa7c2941cb8ba7b3410";
    
    console.log(`Hardcoding overview image to pre-signed URL: ${presignedImageUrl}`);
    setOverviewImageUrl(presignedImageUrl);
    setIsOverviewImageLoading(false);
    setOverviewImageError(null);

    // Original S3 fetching logic commented out for now:
    /*
    const fetchS3OverviewData = async () => { 
      setIsOverviewImageLoading(true);
      setOverviewImageError(null);
      setOverviewImageUrl(null);

      try {
        const s3ListingUrl = `https://${bucketName}.s3.amazonaws.com/?list-type=2&prefix=${encodeURIComponent(regionId)}/&delimiter=/`;
        console.log(`Fetching S3 data for overview image from: ${s3ListingUrl}`);
        const response = await fetch(s3ListingUrl);

        if (!response.ok) {
          throw new Error(`Failed to list S3 bucket contents for overview: ${response.status} ${response.statusText}. Check bucket permissions and CORS policy.`);
        }

        const xmlText = await response.text();
        const parser = new DOMParser();
        const xmlDoc = parser.parseFromString(xmlText, "application/xml");
        const commonPrefixes = Array.from(xmlDoc.getElementsByTagName("CommonPrefixes"));
        
        const dateFolderPrefixes = commonPrefixes.map(cp => {
          const prefixElement = cp.getElementsByTagName("Prefix")[0];
          return prefixElement ? prefixElement.textContent || '' : '';
        }).filter(prefix => prefix && prefix.startsWith(`${regionId}/`) && prefix.endsWith('/'))
          .sort((a, b) => b.localeCompare(a));

        if (dateFolderPrefixes.length > 0) {
          let foundImage = false;
          for (const folderPrefix of dateFolderPrefixes) { 
            const imageUrl = `https://${bucketName}.s3.amazonaws.com/${folderPrefix}RGB.png`;
            try {
              console.log(`Attempting HEAD request for overview image: ${imageUrl}`);
              const imageCheckResponse = await fetch(imageUrl, { method: 'HEAD' });
              if (imageCheckResponse.ok) {
                setOverviewImageUrl(imageUrl);
                console.log(`Displaying overview image: ${imageUrl}`);
                foundImage = true;
                break;
              }
              console.warn(`Overview RGB.png not found or not accessible at ${imageUrl} (status: ${imageCheckResponse.status})`);
            } catch (headError) {
              console.error(`Network or CORS error during HEAD request for ${imageUrl}:`, headError);
            }
          }
          if (!foundImage) {
            setOverviewImageError(`No accessible RGB.png found for region '${regionId}' in the S3 bucket after checking available date folders.`);
          }
        } else {
          setOverviewImageError(`No date folders found for region '${regionId}' in S3 bucket '${bucketName}'. Check if data exists at the expected S3 path.`);
        }
      } catch (error: any) {
        console.error("Error fetching or processing S3 data for overview image:", error);
        setOverviewImageError(error.message || "An unexpected error occurred while loading the overview image data from S3.");
      } finally {
        setIsOverviewImageLoading(false);
      }
    };

    fetchS3OverviewData();
    */
  }, [regionId, s3BucketName]); // s3BucketName is from process.env, effectively constant after build but good practice to list if used

  useEffect(() => {
    const loadSatelliteImages = async () => {
      console.log('[Satellite useEffect] Checking conditions. regionId:', regionId, 'selectedDate:', selectedDate);
      if (selectedDate === '2023-01-15' && regionId === 'brazil-rondonia') {
        setIsSatelliteImagesLoading(true);
        setSatelliteImagesError(null);

        const rgbPresignedUrl = "https://bfl-satellite-imagery-339712843779.s3.us-east-1.amazonaws.com/brazil-rondonia/2023-01-15/RGB.png?response-content-disposition=inline&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEHIaCXVzLWVhc3QtMSJHMEUCICRanIl8cHpk1Nll6D0%2BOGWFDA0vG1VO%2By3JP7hHKdVMAiEA2Q%2F3q7vji0D3WFc3MvoB3E9%2BxgOsZMa%2FiIzwmMItl%2BsqzAMISxAAGgwzMzk3MTI4NDM3NzkiDAOwwCon93I17%2BHgZyqpAzmdAGtjIElFT6HmR84moKaRnQ61tRkPoix7bmig792eI7r81z3cpxnxAG%2BFvGzF2HAA%2BVB%2FpnpCQyr%2F5HYebM%2FfFzTf5y8F5zIcv%2B710746NfG67Qat6MF7XM5vPP0jri3TRBIWzdceD0BufdESnWhjtFiYGVJVS5Ws2naSJF6GwhqwlWWaApDPg%2FbwNgXHuGUlW8BBWFkRJEhyzxqhBo0iVi7IsGCRCXAX2tpI4HUAQ9VDJxhfmECbQJySfxnNIcD2%2FFfYv62HyPj%2Fw1Xv21KhvZYCzHdV9VS7sQPRTwEu7TT6eQfpVXKkcfCiIJUpPsAVRPzCkbVAsgF4zlhn9d1HbByb%2FrfuTNMI5G0DOgYdHqBKOKOFOm6FT48vm4M25MvN0ZZhD%2FlOSfBCUWiCH%2FDDOR%2BpfYpD8El8wjdnYVDQlPjg7sWcpPwSZtpbMOqH1m8G8bAIXAS1L1scvXTksdB86MFlh8RTE0%2BQbQF0SC5Kr0CJsZKm6x62kPetqA2POm9N2iTMVF8fyuE0oWCDkc98CRxI2XIUnR8b5%2BDKs2TG6bDiDEExmPbyMIrZhsIGOt4CtKgKX%2FcbEYWKuhPGzqPi1mcCANYReezxBFTPWrXjbVq2fbAJ%2BfPYo7hhaBlW1Tj2gR2T6UP3RLLMgn7ALzZXSNXutOItUbmeGyttG%2FfoMrEIvlsVIxDcN7kIZpfMAkpEzalmADjdgEk3QOG%2Fp8sYRSf969iSp9LTCkyVqo63eFbGd10D9nM8aXBoVqDf6havz1b5RZV6SAdqa1ScP0hfkQzpxjbxjmVM22yt4aQWJpSBluQfvLtEYP2zOnEhJeVWzd6SMlecxusshub%2F5WgvBtnhKWI5BqEwMasFB%2FP68vnlXlujRPlwg1MUXmArtNM9oW4UYm6RZP%2Fdvn6UvpVeCcGLMWepjPbrO6wflyD%2BjgG2a0AmxO9WXKuVogFSybhWrEwI9%2BBe5nckkQUnDVU8aGKYrpHKrQx4rOTmK8XEQUNLlHwSA6QAiMOvycm2VizoJxyNqM87QgWw5JLN59Y%3D&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=ASIAU6GDWUAB3OBLAASR%2F20250605%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Date=20250605T174533Z&X-Amz-Expires=43200&X-Amz-SignedHeaders=host&X-Amz-Signature=19866cde7bef648f8272a9119508ab7354ebc8d66359cfa7c2941cb8ba7b3410";
        const nbrPresignedUrl = "https://bfl-satellite-imagery-339712843779.s3.us-east-1.amazonaws.com/brazil-rondonia/2023-01-15/NBR.png?response-content-disposition=inline&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEHIaCXVzLWVhc3QtMSJHMEUCICRanIl8cHpk1Nll6D0%2BOGWFDA0vG1VO%2By3JP7hHKdVMAiEA2Q%2F3q7vji0D3WFc3MvoB3E9%2BxgOsZMa%2FiIzwmMItl%2BsqzAMISxAAGgwzMzk3MTI4NDM3NzkiDAOwwCon93I17%2BHgZyqpAzmdAGtjIElFT6HmR84moKaRnQ61tRkPoix7bmig792eI7r81z3cpxnxAG%2BFvGzF2HAA%2BVB%2FpnpCQyr%2F5HYebM%2FfFzTf5y8F5zIcv%2B710746NfG67Qat6MF7XM5vPP0jri3TRBIWzdceD0BufdESnWhjtFiYGVJVS5Ws2naSJF6GwhqwlWWaApDPg%2FbwNgXHuGUlW8BBWFkRJEhyzxqhBo0iVi7IsGCRCXAX2tpI4HUAQ9VDJxhfmECbQJySfxnNIcD2%2FFfYv62HyPj%2Fw1Xv21KhvZYCzHdV9VS7sQPRTwEu7TT6eQfpVXKkcfCiIJUpPsAVRPzCkbVAsgF4zlhn9d1HbByb%2FrfuTNMI5G0DOgYdHqBKOKOFOm6FT48vm4M25MvN0ZZhD%2FlOSfBCUWiCH%2FDDOR%2BpfYpD8El8wjdnYVDQlPjg7sWcpPwSZtpbMOqH1m8G8bAIXAS1L1scvXTksdB86MFlh8RTE0%2BQbQF0SC5Kr0CJsZKm6x62kPetqA2POm9N2iTMVF8fyuE0oWCDkc98CRxI2XIUnR8b5%2BDKs2TG6bDiDEExmPbyMIrZhsIGOt4CtKgKX%2FcbEYWKuhPGzqPi1mcCANYReezxBFTPWrXjbVq2fbAJ%2BfPYo7hhaBlW1Tj2gR2T6UP3RLLMgn7ALzZXSNXutOItUbmeGyttG%2FfoMrEIvlsVIxDcN7kIZpfMAkpEzalmADjdgEk3QOG%2Fp8sYRSf969iSp9LTCkyVqo63eFbGd10D9nM8aXBoVqDf6havz1b5RZV6SAdqa1ScP0hfkQzpxjbxjmVM22yt4aQWJpSBluQfvLtEYP2zOnEhJeVWzd6SMlecxusshub%2F5WgvBtnhKWI5BqEwMasFB%2FP68vnlXlujRPlwg1MUXmArtNM9oW4UYm6RZP%2Fdvn6UvpVeCcGLMWepjPbrO6wflyD%2BjgG2a0AmxO9WXKuVogFSybhWrEwI9%2BBe5nckkQUnDVU8aGKYrpHKrQx4rOTmK8XEQUNLlHwSA6QAiMOvycm2VizoJxyNqM87QgWw5JLN59Y%3D&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=ASIAU6GDWUAB3OBLAASR%2F20250605%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Date=20250605T174855Z&X-Amz-Expires=43200&X-Amz-SignedHeaders=host&X-Amz-Signature=eb2d80385acde9f93cd7bd60a0b59393d8cc2bd5c666dc877f5d927fec80cb5c";
        const ndviPresignedUrl = "https://bfl-satellite-imagery-339712843779.s3.us-east-1.amazonaws.com/brazil-rondonia/2023-01-15/NDVI.png?response-content-disposition=inline&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEHIaCXVzLWVhc3QtMSJHMEUCICRanIl8cHpk1Nll6D0%2BOGWFDA0vG1VO%2By3JP7hHKdVMAiEA2Q%2F3q7vji0D3WFc3MvoB3E9%2BxgOsZMa%2FiIzwmMItl%2BsqzAMISxAAGgwzMzk3MTI4NDM3NzkiDAOwwCon93I17%2BHgZyqpAzmdAGtjIElFT6HmR84moKaRnQ61tRkPoix7bmig792eI7r81z3cpxnxAG%2BFvGzF2HAA%2BVB%2FpnpCQyr%2F5HYebM%2FfFzTf5y8F5zIcv%2B710746NfG67Qat6MF7XM5vPP0jri3TRBIWzdceD0BufdESnWhjtFiYGVJVS5Ws2naSJF6GwhqwlWWaApDPg%2FbwNgXHuGUlW8BBWFkRJEhyzxqhBo0iVi7IsGCRCXAX2tpI4HUAQ9VDJxhfmECbQJySfxnNIcD2%2FFfYv62HyPj%2Fw1Xv21KhvZYCzHdV9VS7sQPRTwEu7TT6eQfpVXKkcfCiIJUpPsAVRPzCkbVAsgF4zlhn9d1HbByb%2FrfuTNMI5G0DOgYdHqBKOKOFOm6FT48vm4M25MvN0ZZhD%2FlOSfBCUWiCH%2FDDOR%2BpfYpD8El8wjdnYVDQlPjg7sWcpPwSZtpbMOqH1m8G8bAIXAS1L1scvXTksdB86MFlh8RTE0%2BQbQF0SC5Kr0CJsZKm6x62kPetqA2POm9N2iTMVF8fyuE0oWCDkc98CRxI2XIUnR8b5%2BDKs2TG6bDiDEExmPbyMIrZhsIGOt4CtKgKX%2FcbEYWKuhPGzqPi1mcCANYReezxBFTPWrXjbVq2fbAJ%2BfPYo7hhaBlW1Tj2gR2T6UP3RLLMgn7ALzZXSNXutOItUbmeGyttG%2FfoMrEIvlsVIxDcN7kIZpfMAkpEzalmADjdgEk3QOG%2Fp8sYRSf969iSp9LTCkyVqo63eFbGd10D9nM8aXBoVqDf6havz1b5RZV6SAdqa1ScP0hfkQzpxjbxjmVM22yt4aQWJpSBluQfvLtEYP2zOnEhJeVWzd6SMlecxusshub%2F5WgvBtnhKWI5BqEwMasFB%2FP68vnlXlujRPlwg1MUXmArtNM9oW4UYm6RZP%2Fdvn6UvpVeCcGLMWepjPbrO6wflyD%2BjgG2a0AmxO9WXKuVogFSybhWrEwI9%2BBe5nckkQUnDVU8aGKYrpHKrQx4rOTmK8XEQUNLlHwSA6QAiMOvycm2VizoJxyNqM87QgWw5JLN59Y%3D&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=ASIAU6GDWUAB3OBLAASR%2F20250605%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Date=20250605T174936Z&X-Amz-Expires=43200&X-Amz-SignedHeaders=host&X-Amz-Signature=f878eba55c8f473e796566311217c07d688e6ed6051105900885002100889267";

        const newImageUrls = {
          rgb: rgbPresignedUrl,
          ndvi: ndviPresignedUrl,
          nbr: nbrPresignedUrl
        };
        console.log('[Satellite useEffect] URLs set to:', { rgb: 'rgbPresignedUrl_FULL', ndvi: 'ndviPresignedUrl_FULL', nbr: 'nbrPresignedUrl_FULL' }); // Log placeholders for brevity
        setSatelliteImageUrls(newImageUrls);
        setIsSatelliteImagesLoading(false);
      } else {
        console.log('[Satellite useEffect] Condition NOT MET. Clearing URLs.');
        setSatelliteImageUrls({});
        setIsSatelliteImagesLoading(false);
      }
    };
    loadSatelliteImages();
  }, [selectedDate, regionId]);

  const handleDateChange = (from: Date | undefined, to: Date | undefined) => {
    if (!availableDates.length || !from || !to) {
      setFromDate(from)
      setToDate(to)
      return
    }
    const parse = (s: string) => new Date(s)
    const fromStr = availableDates.reduce((p, c) =>
      Math.abs(parse(c).getTime() - from.getTime()) < Math.abs(parse(p).getTime() - from.getTime()) ? c : p
    , availableDates[0])
    const toStr = availableDates.reduce((p, c) =>
      Math.abs(parse(c).getTime() - to.getTime()) < Math.abs(parse(p).getTime() - to.getTime()) ? c : p
    , availableDates[0])
    setFromDate(parse(fromStr))
    setToDate(parse(toStr))
  };

  console.log('[Dashboard Page Render] regionId:', regionId, 'selectedDate:', selectedDate, 'selectedSatelliteProductType:', selectedSatelliteProductType, 'satelliteImageUrls:', satelliteImageUrls);
  return (
    <SidebarProvider>
      <AppSidebar />
      <SidebarInset>
        <header className="flex h-16 shrink-0 items-center gap-2">
          <div className="flex items-center gap-2 px-4">
            <SidebarTrigger className="-ml-1" />
            <Separator
              orientation="vertical"
              className="mr-2 data-[orientation=vertical]:h-4"
            />
            <Breadcrumb>
              <BreadcrumbList>
                <BreadcrumbItem className="hidden md:block">
                  <BreadcrumbLink href="/">
                    Conservation Initiative
                  </BreadcrumbLink>
                </BreadcrumbItem>
                <BreadcrumbSeparator className="hidden md:block" />
                <BreadcrumbItem>
                  <BreadcrumbPage>Satellite Analysis</BreadcrumbPage>
                </BreadcrumbItem>
              </BreadcrumbList>
            </Breadcrumb>
          </div>
        </header>
        <div className="flex flex-1 flex-col gap-4 p-4 pt-0">

          
          <Tabs defaultValue="overview" className="space-y-4">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="overview">
                <Map className="mr-2 h-4 w-4" />
                Overview
              </TabsTrigger>
              <TabsTrigger value="satellite">
                <Map className="mr-2 h-4 w-4" />
                Satellite
              </TabsTrigger>
            </TabsList>

            

            
            <TabsContent value="overview" className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
                <Card className="lg:col-span-7">
                  <CardHeader>
                    <CardTitle>Fire Damage Map</CardTitle>
                    <CardDescription>
                      High-resolution satellite imagery of affected areas
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="p-0">
                    {isOverviewImageLoading && <p className="text-center text-muted-foreground">Loading map...</p>}
                    {overviewImageError && <p className="text-center text-red-500">Error: {overviewImageError}</p>}
                    {overviewImageUrl && !isOverviewImageLoading && !overviewImageError && (
                      <img
                        src={overviewImageUrl}
                        alt={`Overview map for ${regionId}`}
                        className="w-full h-auto rounded-md object-contain max-h-[600px]"
                      />
                    )}
                    {!isOverviewImageLoading && !overviewImageUrl && !overviewImageError && (
                      <p className="text-center text-muted-foreground">No overview map available for this region.</p>
                    )}
                  </CardContent>
                </Card>
              </div>
            </TabsContent>
            <TabsContent value="satellite" className="space-y-4">
              <div className="grid gap-4 md:grid-cols-1 lg:grid-cols-4">
                <div className="lg:col-span-3">
                  <Card>
                    <CardHeader>
                      <CardTitle>Satellite Images</CardTitle>
                      <CardDescription>
                        Satellite images for the selected date and region
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div className="flex space-x-2 mb-4">
                        {(['rgb', 'ndvi', 'nbr'] as Array<keyof SatelliteImageUrls>).map((type) => (
                          <Button
                            key={type}
                            variant={selectedSatelliteProductType === type ? 'default' : 'outline'}
                            onClick={() => setSelectedSatelliteProductType(type)}
                          >
                            {type.toUpperCase()}
                          </Button>
                        ))}
                      </div>

                      {isSatelliteImagesLoading && <p>Loading satellite images...</p>}
                      {satelliteImagesError && <p className="text-red-500">{satelliteImagesError}</p>}
                      
                      {!isSatelliteImagesLoading && !satelliteImagesError && (
                        <>
                          {selectedSatelliteProductType === 'rgb' && satelliteImageUrls.rgb && (
                            <div>
                              <h3 className="text-lg font-semibold mb-2">RGB Image</h3>
                              <img src={satelliteImageUrls.rgb} alt="RGB Satellite Image" className="w-full h-auto rounded-md border object-contain" style={{ maxHeight: '60vh' }} />
                            </div>
                          )}
                          {selectedSatelliteProductType === 'ndvi' && satelliteImageUrls.ndvi && (
                            <div>
                              <h3 className="text-lg font-semibold mb-2">NDVI Image</h3>
                              <img src={satelliteImageUrls.ndvi} alt="NDVI Satellite Image" className="w-full h-auto rounded-md border object-contain" style={{ maxHeight: '60vh' }} />
                            </div>
                          )}
                          {selectedSatelliteProductType === 'nbr' && satelliteImageUrls.nbr && (
                            <div>
                              <h3 className="text-lg font-semibold mb-2">NBR Image</h3>
                              <img src={satelliteImageUrls.nbr} alt="NBR Satellite Image" className="w-full h-auto rounded-md border object-contain" style={{ maxHeight: '60vh' }} />
                            </div>
                          )}
                          {(!satelliteImageUrls[selectedSatelliteProductType]) && (
                             <p>No {selectedSatelliteProductType.toUpperCase()} image available for the selected date ({selectedDate}) and region ({regionId}) with the current hardcoded URLs.</p>
                          )}
                        </>
                      )}
                    </CardContent>
                  </Card>
                </div>
                <div className="space-y-4">
                  <TimeComparisonControls
                    availableDates={availableDates.map(dt => new Date(dt))}
                    onChange={handleDateChange}
                  />
                  <DataDownload regionId={regionId} fromDate={fromDate} toDate={toDate} />
                </div>
              </div>
            </TabsContent>
          </Tabs>
        </div>
      </SidebarInset>
    </SidebarProvider>
  )
}
