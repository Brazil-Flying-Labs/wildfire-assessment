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
import { AlertTriangle, Flame, Map, Calendar, Activity } from "lucide-react"

export default function FireDamagePage() {
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
                  <BreadcrumbLink href="/dashboard">
                    Dashboard
                  </BreadcrumbLink>
                </BreadcrumbItem>
                <BreadcrumbSeparator className="hidden md:block" />
                <BreadcrumbItem>
                  <BreadcrumbPage>Fire Damage Assessment</BreadcrumbPage>
                </BreadcrumbItem>
              </BreadcrumbList>
            </Breadcrumb>
          </div>
        </header>
        <div className="flex flex-1 flex-col gap-4 p-4 pt-0">
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium">Total Affected Area</CardTitle>
                <Flame className="size-4 text-destructive" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">8,806 hectares</div>
                <p className="text-xs text-muted-foreground">
                  70% of monitored region
                </p>
                <Progress className="mt-3" value={70} />
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium">Severe Damage</CardTitle>
                <AlertTriangle className="size-4 text-destructive" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">3,698 hectares</div>
                <p className="text-xs text-muted-foreground">
                  42% of affected area
                </p>
                <Progress className="mt-3" value={42} />
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium">AI Confidence</CardTitle>
                <Activity className="size-4 text-primary" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">94.2%</div>
                <p className="text-xs text-muted-foreground">
                  Based on 1,240 verified samples
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium">Fire Event Duration</CardTitle>
                <Calendar className="size-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">11 days</div>
                <p className="text-xs text-muted-foreground">
                  Feb 15 - Feb 26, 2025
                </p>
              </CardContent>
            </Card>
          </div>
          
          <Tabs defaultValue="damage-map" className="space-y-4">
            <TabsList>
              <TabsTrigger value="damage-map">Damage Map</TabsTrigger>
              <TabsTrigger value="classification">Classification</TabsTrigger>
              <TabsTrigger value="environmental-impact">Environmental Impact</TabsTrigger>
              <TabsTrigger value="timeline">Timeline</TabsTrigger>
            </TabsList>
            <TabsContent value="damage-map" className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle>Fire Damage Map</CardTitle>
                  <CardDescription>Showing damage severity across São Paulo region</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="aspect-video bg-muted rounded-md flex items-center justify-center">
                    <div className="text-center">
                      <Map className="size-10 mx-auto text-muted-foreground" />
                      <p className="text-sm text-muted-foreground mt-2">Interactive fire damage map</p>
                    </div>
                  </div>
                  <div className="grid grid-cols-4 gap-2 text-sm mt-4">
                    <div className="flex items-center gap-2">
                      <div className="size-3 rounded-full bg-red-500"></div>
                      <span>Severe (42%)</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="size-3 rounded-full bg-orange-400"></div>
                      <span>Moderate (35%)</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="size-3 rounded-full bg-yellow-300"></div>
                      <span>Mild (23%)</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="size-3 rounded-full bg-green-300"></div>
                      <span>Unaffected</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
            <TabsContent value="classification" className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle>AI Classification Analysis</CardTitle>
                  <CardDescription>Machine learning classification of fire damage</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div>
                      <div className="flex justify-between mb-1">
                        <span className="text-sm">Severe Damage</span>
                        <span className="text-sm font-medium">42%</span>
                      </div>
                      <Progress value={42} className="h-2" />
                      <p className="text-xs text-muted-foreground mt-1">Complete vegetation loss, soil damage</p>
                    </div>
                    <div>
                      <div className="flex justify-between mb-1">
                        <span className="text-sm">Moderate Damage</span>
                        <span className="text-sm font-medium">35%</span>
                      </div>
                      <Progress value={35} className="h-2" />
                      <p className="text-xs text-muted-foreground mt-1">Partial canopy loss, understory burned</p>
                    </div>
                    <div>
                      <div className="flex justify-between mb-1">
                        <span className="text-sm">Mild Damage</span>
                        <span className="text-sm font-medium">23%</span>
                      </div>
                      <Progress value={23} className="h-2" />
                      <p className="text-xs text-muted-foreground mt-1">Ground cover burned, canopy intact</p>
                    </div>
                    <div className="pt-4">
                      <div className="text-sm font-medium mb-2">Classification Confidence</div>
                      <div className="grid grid-cols-2 gap-4">
                        <Card className="p-3">
                          <div className="text-sm font-medium">Model Accuracy</div>
                          <div className="text-xl font-bold">94.2%</div>
                          <p className="text-xs text-muted-foreground">Based on ground truth data</p>
                        </Card>
                        <Card className="p-3">
                          <div className="text-sm font-medium">Validation Samples</div>
                          <div className="text-xl font-bold">1,240</div>
                          <p className="text-xs text-muted-foreground">Field-verified points</p>
                        </Card>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
            <TabsContent value="environmental-impact" className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle>Environmental Impact</CardTitle>
                  <CardDescription>Assessment of fire effects on ecosystem</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div>
                      <div className="flex justify-between mb-1">
                        <span className="text-sm">Biodiversity Impact</span>
                        <span className="text-sm font-medium">High</span>
                      </div>
                      <Progress value={85} className="h-2" />
                      <p className="text-xs text-muted-foreground mt-1">15 endangered species affected</p>
                    </div>
                    <div>
                      <div className="flex justify-between mb-1">
                        <span className="text-sm">Water Resources</span>
                        <span className="text-sm font-medium">Moderate</span>
                      </div>
                      <Progress value={65} className="h-2" />
                      <p className="text-xs text-muted-foreground mt-1">3 watersheds affected by ash and debris</p>
                    </div>
                    <div>
                      <div className="flex justify-between mb-1">
                        <span className="text-sm">Soil Degradation</span>
                        <span className="text-sm font-medium">Severe</span>
                      </div>
                      <Progress value={78} className="h-2" />
                      <p className="text-xs text-muted-foreground mt-1">Increased erosion risk in 68% of affected areas</p>
                    </div>
                    <div>
                      <div className="flex justify-between mb-1">
                        <span className="text-sm">Carbon Release</span>
                        <span className="text-sm font-medium">High</span>
                      </div>
                      <Progress value={82} className="h-2" />
                      <p className="text-xs text-muted-foreground mt-1">Estimated 420,000 tons of CO₂ released</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
            <TabsContent value="timeline" className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle>Fire Event Timeline</CardTitle>
                  <CardDescription>Chronological progression of the wildfire</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="flex items-start gap-4 border-l-2 border-red-500 pl-4 pb-6">
                      <div>
                        <div className="font-medium">Feb 15, 2025</div>
                        <div className="text-sm text-muted-foreground">Fire ignition detected</div>
                        <p className="text-sm mt-1">Initial hotspot detected in northern sector of Luiz Antônio Station, likely human-caused.</p>
                      </div>
                    </div>
                    <div className="flex items-start gap-4 border-l-2 border-red-500 pl-4 pb-6">
                      <div>
                        <div className="font-medium">Feb 17, 2025</div>
                        <div className="text-sm text-muted-foreground">Rapid expansion</div>
                        <p className="text-sm mt-1">Fire spread to 3,200 hectares due to strong winds and dry conditions.</p>
                      </div>
                    </div>
                    <div className="flex items-start gap-4 border-l-2 border-red-500 pl-4 pb-6">
                      <div>
                        <div className="font-medium">Feb 20, 2025</div>
                        <div className="text-sm text-muted-foreground">Peak intensity</div>
                        <p className="text-sm mt-1">Fire reached maximum intensity, affecting 7,500 hectares with crown fires in mature forest.</p>
                      </div>
                    </div>
                    <div className="flex items-start gap-4 border-l-2 border-green-500 pl-4">
                      <div>
                        <div className="font-medium">Feb 26, 2025</div>
                        <div className="text-sm text-muted-foreground">Containment achieved</div>
                        <p className="text-sm mt-1">Fire fully contained after rainfall and firefighting efforts. Final affected area: 8,806 hectares.</p>
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
