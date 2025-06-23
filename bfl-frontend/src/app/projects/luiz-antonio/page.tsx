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
import {  Flame, Leaf, Map, Activity, TreePine, Bird } from "lucide-react"
import { StationMap } from "@/components/station-map"

export default function LuizAntonioPage() {
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
                  <BreadcrumbLink href="/projects">
                    Projects
                  </BreadcrumbLink>
                </BreadcrumbItem>
                <BreadcrumbSeparator className="hidden md:block" />
                <BreadcrumbItem>
                  <BreadcrumbPage>Luiz Antônio Station</BreadcrumbPage>
                </BreadcrumbItem>
              </BreadcrumbList>
            </Breadcrumb>
          </div>
        </header>
        <div className="flex flex-1 flex-col gap-4 p-4 pt-0">
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium">Total Area</CardTitle>
                <Map className="size-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">4,532 hectares</div>
                <p className="text-xs text-muted-foreground">
                  Protected ecological station
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium">Fire-Affected Area</CardTitle>
                <Flame className="size-4 text-destructive" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">3,172 hectares</div>
                <p className="text-xs text-muted-foreground">
                  70% of station affected
                </p>
                <Progress className="mt-3" value={70} />
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium">Recovery Progress</CardTitle>
                <Leaf className="size-4 text-primary" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">26%</div>
                <p className="text-xs text-muted-foreground">
                  Slightly above regional average
                </p>
                <Progress className="mt-3" value={26} />
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium">Biodiversity Status</CardTitle>
                <Bird className="size-4 text-amber-500" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">At Risk</div>
                <p className="text-xs text-muted-foreground">
                  8 endangered species affected
                </p>
              </CardContent>
            </Card>
          </div>
          
          <Tabs defaultValue="overview" className="space-y-4">
            <TabsList>
              <TabsTrigger value="overview">Overview</TabsTrigger>
              <TabsTrigger value="ecosystems">Ecosystems</TabsTrigger>
              <TabsTrigger value="conservation">Conservation</TabsTrigger>
              <TabsTrigger value="research">Research</TabsTrigger>
            </TabsList>
            <TabsContent value="overview" className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <StationMap />
                <Card>
                  <CardHeader>
                    <CardTitle>Station Information</CardTitle>
                    <CardDescription>Key details about Luiz Antônio Station</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      <div className="grid grid-cols-2 gap-x-4 gap-y-2">
                        <div className="text-sm font-medium">Established</div>
                        <div className="text-sm">1982</div>
                        
                        <div className="text-sm font-medium">Location</div>
                        <div className="text-sm">São Paulo State, Brazil</div>
                        
                        <div className="text-sm font-medium">Biome</div>
                        <div className="text-sm">Cerrado / Atlantic Forest transition</div>
                        
                        <div className="text-sm font-medium">Management</div>
                        <div className="text-sm">Instituto Florestal de São Paulo</div>
                        
                        <div className="text-sm font-medium">Research Focus</div>
                        <div className="text-sm">Biodiversity, Fire Ecology, Conservation</div>
                        
                        <div className="text-sm font-medium">Conservation Status</div>
                        <div className="text-sm">Protected Ecological Station</div>
                      </div>
                      
                      <div className="pt-2">
                        <p className="text-sm">
                          The Luiz Antônio Ecological Station is a protected area in São Paulo state that preserves a critical transition zone between Cerrado savanna and Atlantic Forest ecosystems. The station has been significantly impacted by recent wildfires but serves as an important research site for fire ecology and ecosystem recovery.
                        </p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </TabsContent>
            <TabsContent value="ecosystems" className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle>Ecosystem Composition</CardTitle>
                  <CardDescription>Major ecosystem types within the station</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div>
                      <div className="flex justify-between mb-1">
                        <span className="text-sm">Cerrado Savanna</span>
                        <span className="text-sm font-medium">48%</span>
                      </div>
                      <Progress value={48} className="h-2" />
                      <p className="text-xs text-muted-foreground mt-1">Open grasslands with scattered trees and shrubs</p>
                    </div>
                    <div>
                      <div className="flex justify-between mb-1">
                        <span className="text-sm">Cerradão (Dense Savanna)</span>
                        <span className="text-sm font-medium">22%</span>
                      </div>
                      <Progress value={22} className="h-2" />
                      <p className="text-xs text-muted-foreground mt-1">Denser woodland with savanna characteristics</p>
                    </div>
                    <div>
                      <div className="flex justify-between mb-1">
                        <span className="text-sm">Atlantic Forest Fragments</span>
                        <span className="text-sm font-medium">18%</span>
                      </div>
                      <Progress value={18} className="h-2" />
                      <p className="text-xs text-muted-foreground mt-1">Humid forest with high biodiversity</p>
                    </div>
                    <div>
                      <div className="flex justify-between mb-1">
                        <span className="text-sm">Riparian Forests</span>
                        <span className="text-sm font-medium">12%</span>
                      </div>
                      <Progress value={12} className="h-2" />
                      <p className="text-xs text-muted-foreground mt-1">Forests along water courses</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
              <Card>
                <CardHeader>
                  <CardTitle>Fire Impact by Ecosystem</CardTitle>
                  <CardDescription>Differential impact across ecosystem types</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-4">
                      <div>
                        <div className="flex justify-between mb-1">
                          <span className="text-sm">Cerrado Savanna</span>
                          <span className="text-sm font-medium">High Impact</span>
                        </div>
                        <Progress value={85} className="h-2" />
                        <p className="text-xs text-muted-foreground mt-1">85% affected, but adapted to fire regimes</p>
                      </div>
                      <div>
                        <div className="flex justify-between mb-1">
                          <span className="text-sm">Cerradão</span>
                          <span className="text-sm font-medium">Severe Impact</span>
                        </div>
                        <Progress value={92} className="h-2" />
                        <p className="text-xs text-muted-foreground mt-1">92% affected, slower recovery expected</p>
                      </div>
                    </div>
                    <div className="space-y-4">
                      <div>
                        <div className="flex justify-between mb-1">
                          <span className="text-sm">Atlantic Forest</span>
                          <span className="text-sm font-medium">Moderate Impact</span>
                        </div>
                        <Progress value={45} className="h-2" />
                        <p className="text-xs text-muted-foreground mt-1">45% affected, not fire-adapted</p>
                      </div>
                      <div>
                        <div className="flex justify-between mb-1">
                          <span className="text-sm">Riparian Forests</span>
                          <span className="text-sm font-medium">Low Impact</span>
                        </div>
                        <Progress value={28} className="h-2" />
                        <p className="text-xs text-muted-foreground mt-1">28% affected, protected by moisture</p>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
            <TabsContent value="conservation" className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle>Conservation Priorities</CardTitle>
                  <CardDescription>Current conservation focus areas</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="flex items-start gap-4 border-b pb-4">
                      <div className="bg-red-500/10 p-2 rounded-full">
                        <TreePine className="size-5 text-red-500" />
                      </div>
                      <div>
                        <p className="font-medium">Atlantic Forest Fragment Protection</p>
                        <p className="text-sm text-muted-foreground">Preserving remaining unburned fragments of Atlantic Forest</p>
                        <div className="flex items-center gap-2 mt-1">
                          <span className="text-xs bg-red-100 text-red-800 px-2 py-1 rounded-full">High Priority</span>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-start gap-4 border-b pb-4">
                      <div className="bg-blue-500/10 p-2 rounded-full">
                        <Activity className="size-5 text-blue-500" />
                      </div>
                      <div>
                        <p className="font-medium">Watershed Protection</p>
                        <p className="text-sm text-muted-foreground">Preventing erosion and sedimentation in key watersheds</p>
                        <div className="flex items-center gap-2 mt-1">
                          <span className="text-xs bg-amber-100 text-amber-800 px-2 py-1 rounded-full">Medium Priority</span>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-start gap-4">
                      <div className="bg-green-500/10 p-2 rounded-full">
                        <Bird className="size-5 text-green-500" />
                      </div>
                      <div>
                        <p className="font-medium">Endangered Species Monitoring</p>
                        <p className="text-sm text-muted-foreground">Tracking and protecting critical species post-fire</p>
                        <div className="flex items-center gap-2 mt-1">
                          <span className="text-xs bg-red-100 text-red-800 px-2 py-1 rounded-full">High Priority</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
            <TabsContent value="research" className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle>Active Research Projects</CardTitle>
                  <CardDescription>Current scientific studies at the station</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="flex items-center justify-between border-b pb-4">
                      <div>
                        <p className="font-medium">Post-Fire Vegetation Recovery Dynamics</p>
                        <p className="text-sm text-muted-foreground">University of São Paulo</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded-full">Active</span>
                      </div>
                    </div>
                    <div className="flex items-center justify-between border-b pb-4">
                      <div>
                        <p className="font-medium">Biodiversity Response to Wildfire</p>
                        <p className="text-sm text-muted-foreground">National Institute for Amazonian Research</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded-full">Active</span>
                      </div>
                    </div>
                    <div className="flex items-center justify-between border-b pb-4">
                      <div>
                        <p className="font-medium">Remote Sensing for Ecosystem Monitoring</p>
                        <p className="text-sm text-muted-foreground">Brazil Flying Labs</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded-full">Active</span>
                      </div>
                    </div>
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-medium">Carbon Flux in Fire-Affected Ecosystems</p>
                        <p className="text-sm text-muted-foreground">Federal University of São Carlos</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded-full">Planned</span>
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
