import { AppSidebar } from "@/components/app-sidebar"
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
import { Calendar, Map, Activity, Settings } from "lucide-react"

export default function SatelliteMonitoringPage() {
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
                  <BreadcrumbLink href="/monitoring">
                    Monitoring
                  </BreadcrumbLink>
                </BreadcrumbItem>
                <BreadcrumbSeparator className="hidden md:block" />
                <BreadcrumbItem>
                  <BreadcrumbPage>Satellite Imagery</BreadcrumbPage>
                </BreadcrumbItem>
              </BreadcrumbList>
            </Breadcrumb>
          </div>
        </header>
        <div className="flex flex-1 flex-col gap-4 p-4 pt-0">
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium">Latest Imagery</CardTitle>
                <Calendar className="size-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">Feb 28, 2025</div>
                <p className="text-xs text-muted-foreground">
                  Sentinel-2 satellite pass
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium">Cloud Cover</CardTitle>
                <div className="size-4 text-muted-foreground">%</div>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">12%</div>
                <p className="text-xs text-muted-foreground">
                  Excellent visibility conditions
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium">Available Scenes</CardTitle>
                <Activity className="size-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">14</div>
                <p className="text-xs text-muted-foreground">
                  Last 30 days
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium">Processing Status</CardTitle>
                <Activity className="size-4 text-green-500" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">Complete</div>
                <p className="text-xs text-muted-foreground">
                  All imagery processed
                </p>
              </CardContent>
            </Card>
          </div>
          
          <Tabs defaultValue="imagery" className="space-y-4">
            <TabsList>
              <TabsTrigger value="imagery">Satellite Imagery</TabsTrigger>
              <TabsTrigger value="analysis">Satellite Analysis</TabsTrigger>
              <TabsTrigger value="archive">Imagery Archive</TabsTrigger>
              <TabsTrigger value="settings">Monitoring Settings</TabsTrigger>
            </TabsList>
            <TabsContent value="imagery" className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle>Satellite Imagery</CardTitle>
                  <CardDescription>Latest processed imagery of fire-affected areas</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="aspect-video bg-muted rounded-md flex items-center justify-center">
                    <div className="text-center">
                      <Map className="size-10 mx-auto text-muted-foreground" />
                      <p className="text-sm text-muted-foreground mt-2">Satellite imagery view</p>
                    </div>
                  </div>
                  <div className="grid grid-cols-4 gap-2 text-sm mt-4">
                    <div className="flex items-center gap-2">
                      <div className="size-3 rounded-full bg-blue-500"></div>
                      <span>True Color</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="size-3 rounded-full bg-green-500"></div>
                      <span>NDVI</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="size-3 rounded-full bg-red-500"></div>
                      <span>Burn Scar</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="size-3 rounded-full bg-purple-500"></div>
                      <span>Moisture</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
            <TabsContent value="analysis" className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle>Satellite Analysis</CardTitle>
                  <CardDescription>AI-powered analysis of satellite imagery</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-4">
                      <div className="aspect-square bg-muted rounded-md flex items-center justify-center">
                        <div className="text-center">
                          <Activity className="size-10 mx-auto text-muted-foreground" />
                          <p className="text-sm text-muted-foreground mt-2">NDVI Analysis</p>
                        </div>
                      </div>
                      <div className="space-y-2">
                        <div className="flex justify-between">
                          <span className="text-sm">Healthy Vegetation</span>
                          <span className="text-sm font-medium">23%</span>
                        </div>
                        <Progress value={23} className="h-2" />
                        <div className="flex justify-between">
                          <span className="text-sm">Recovering Vegetation</span>
                          <span className="text-sm font-medium">45%</span>
                        </div>
                        <Progress value={45} className="h-2" />
                        <div className="flex justify-between">
                          <span className="text-sm">Damaged Areas</span>
                          <span className="text-sm font-medium">32%</span>
                        </div>
                        <Progress value={32} className="h-2" />
                      </div>
                    </div>
                    <div className="space-y-4">
                      <div className="aspect-square bg-muted rounded-md flex items-center justify-center">
                        <div className="text-center">
                          <Activity className="size-10 mx-auto text-muted-foreground" />
                          <p className="text-sm text-muted-foreground mt-2">Burn Scar Analysis</p>
                        </div>
                      </div>
                      <div className="space-y-2">
                        <div className="flex justify-between">
                          <span className="text-sm">Severe Burn</span>
                          <span className="text-sm font-medium">42%</span>
                        </div>
                        <Progress value={42} className="h-2" />
                        <div className="flex justify-between">
                          <span className="text-sm">Moderate Burn</span>
                          <span className="text-sm font-medium">35%</span>
                        </div>
                        <Progress value={35} className="h-2" />
                        <div className="flex justify-between">
                          <span className="text-sm">Light Burn</span>
                          <span className="text-sm font-medium">23%</span>
                        </div>
                        <Progress value={23} className="h-2" />
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
            <TabsContent value="archive" className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle>Imagery Archive</CardTitle>
                  <CardDescription>Historical satellite imagery</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="flex items-center justify-between border-b pb-4">
                      <div>
                        <p className="font-medium">Sentinel-2 Imagery</p>
                        <p className="text-sm text-muted-foreground">Feb 28, 2025</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded-full">Latest</span>
                      </div>
                    </div>
                    <div className="flex items-center justify-between border-b pb-4">
                      <div>
                        <p className="font-medium">Sentinel-2 Imagery</p>
                        <p className="text-sm text-muted-foreground">Feb 18, 2025</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded-full">Processed</span>
                      </div>
                    </div>
                    <div className="flex items-center justify-between border-b pb-4">
                      <div>
                        <p className="font-medium">Landsat-9 Imagery</p>
                        <p className="text-sm text-muted-foreground">Feb 15, 2025</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded-full">Processed</span>
                      </div>
                    </div>
                    <div className="flex items-center justify-between border-b pb-4">
                      <div>
                        <p className="font-medium">Sentinel-2 Imagery</p>
                        <p className="text-sm text-muted-foreground">Feb 8, 2025</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded-full">Processed</span>
                      </div>
                    </div>
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-medium">Landsat-9 Imagery</p>
                        <p className="text-sm text-muted-foreground">Jan 30, 2025</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded-full">Processed</span>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
            <TabsContent value="settings" className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle>Monitoring Settings</CardTitle>
                  <CardDescription>Configure satellite monitoring parameters</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="flex items-start gap-4 border-b pb-4">
                      <div className="bg-blue-500/10 p-2 rounded-full">
                        <Settings className="size-5 text-blue-500" />
                      </div>
                      <div>
                        <p className="font-medium">Data Sources</p>
                        <p className="text-sm text-muted-foreground">Configure which satellite platforms to use</p>
                        <div className="flex flex-wrap gap-2 mt-2">
                          <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded-full">Sentinel-2</span>
                          <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded-full">Landsat-9</span>
                          <span className="text-xs bg-gray-100 text-gray-800 px-2 py-1 rounded-full">Planet (disabled)</span>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-start gap-4 border-b pb-4">
                      <div className="bg-green-500/10 p-2 rounded-full">
                        <Settings className="size-5 text-green-500" />
                      </div>
                      <div>
                        <p className="font-medium">Analysis Algorithms</p>
                        <p className="text-sm text-muted-foreground">Select which analysis to run on imagery</p>
                        <div className="flex flex-wrap gap-2 mt-2">
                          <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded-full">NDVI</span>
                          <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded-full">NBR</span>
                          <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded-full">Burn Scar</span>
                          <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded-full">Land Cover</span>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-start gap-4">
                      <div className="bg-amber-500/10 p-2 rounded-full">
                        <Calendar className="size-5 text-amber-500" />
                      </div>
                      <div>
                        <p className="font-medium">Monitoring Schedule</p>
                        <p className="text-sm text-muted-foreground">Set frequency of data acquisition and processing</p>
                        <div className="flex flex-wrap gap-2 mt-2">
                          <span className="text-xs bg-amber-100 text-amber-800 px-2 py-1 rounded-full">Every 10 days</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </div>
      </SidebarInset>
    </SidebarProvider>
  )
}
