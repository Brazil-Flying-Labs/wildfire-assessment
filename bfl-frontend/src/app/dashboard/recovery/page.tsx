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
import { Calendar, Leaf, TrendingUp, Activity } from "lucide-react"

export default function RecoveryPage() {
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
                  <BreadcrumbPage>Recovery Tracking</BreadcrumbPage>
                </BreadcrumbItem>
              </BreadcrumbList>
            </Breadcrumb>
          </div>
        </header>
        <div className="flex flex-1 flex-col gap-4 p-4 pt-0">
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium">Recovery Progress</CardTitle>
                <Leaf className="size-4 text-primary" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">23%</div>
                <p className="text-xs text-muted-foreground">
                  Based on vegetation regrowth
                </p>
                <Progress className="mt-3" value={23} />
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium">Monthly Growth</CardTitle>
                <TrendingUp className="size-4 text-green-500" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">+5.2%</div>
                <p className="text-xs text-muted-foreground">
                  Compared to +4.8% last month
                </p>
                <Progress className="mt-3" value={52} />
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium">Last Assessment</CardTitle>
                <Calendar className="size-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">Feb 28, 2025</div>
                <p className="text-xs text-muted-foreground">
                  Next update in 3 days
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium">Est. Full Recovery</CardTitle>
                <Calendar className="size-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">~3.5 years</div>
                <p className="text-xs text-muted-foreground">
                  Based on current growth rate
                </p>
              </CardContent>
            </Card>
          </div>
          
          <Tabs defaultValue="vegetation" className="space-y-4">
            <TabsList>
              <TabsTrigger value="vegetation">Vegetation Analysis</TabsTrigger>
              <TabsTrigger value="biodiversity">Biodiversity</TabsTrigger>
              <TabsTrigger value="timelapse">Recovery Time-lapse</TabsTrigger>
              <TabsTrigger value="interventions">Recovery Interventions</TabsTrigger>
            </TabsList>
            <TabsContent value="vegetation" className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle>Vegetation Recovery Analysis</CardTitle>
                  <CardDescription>NDVI comparison over time</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="aspect-video bg-muted rounded-md flex items-center justify-center">
                    <div className="text-center">
                      <TrendingUp className="size-10 mx-auto text-muted-foreground" />
                      <p className="text-sm text-muted-foreground mt-2">Vegetation recovery time series</p>
                    </div>
                  </div>
                  <div className="grid grid-cols-3 gap-4 mt-4">
                    <div className="space-y-1">
                      <div className="text-sm font-medium">Canopy Cover</div>
                      <div className="text-2xl font-bold">18%</div>
                      <Progress value={18} className="h-2" />
                      <p className="text-xs text-muted-foreground">Of pre-fire levels</p>
                    </div>
                    <div className="space-y-1">
                      <div className="text-sm font-medium">Understory</div>
                      <div className="text-2xl font-bold">31%</div>
                      <Progress value={31} className="h-2" />
                      <p className="text-xs text-muted-foreground">Of pre-fire levels</p>
                    </div>
                    <div className="space-y-1">
                      <div className="text-sm font-medium">Ground Cover</div>
                      <div className="text-2xl font-bold">42%</div>
                      <Progress value={42} className="h-2" />
                      <p className="text-xs text-muted-foreground">Of pre-fire levels</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
            <TabsContent value="biodiversity" className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle>Biodiversity Recovery</CardTitle>
                  <CardDescription>Species return monitoring</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div>
                      <div className="flex justify-between mb-1">
                        <span className="text-sm">Mammals</span>
                        <span className="text-sm font-medium">15 species observed</span>
                      </div>
                      <Progress value={38} className="h-2" />
                      <p className="text-xs text-muted-foreground mt-1">38% of pre-fire biodiversity</p>
                    </div>
                    <div>
                      <div className="flex justify-between mb-1">
                        <span className="text-sm">Birds</span>
                        <span className="text-sm font-medium">47 species observed</span>
                      </div>
                      <Progress value={52} className="h-2" />
                      <p className="text-xs text-muted-foreground mt-1">52% of pre-fire biodiversity</p>
                    </div>
                    <div>
                      <div className="flex justify-between mb-1">
                        <span className="text-sm">Insects</span>
                        <span className="text-sm font-medium">126 species observed</span>
                      </div>
                      <Progress value={45} className="h-2" />
                      <p className="text-xs text-muted-foreground mt-1">45% of pre-fire biodiversity</p>
                    </div>
                    <div>
                      <div className="flex justify-between mb-1">
                        <span className="text-sm">Plants</span>
                        <span className="text-sm font-medium">83 species observed</span>
                      </div>
                      <Progress value={29} className="h-2" />
                      <p className="text-xs text-muted-foreground mt-1">29% of pre-fire biodiversity</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
              <Card>
                <CardHeader>
                  <CardTitle>Key Species Monitoring</CardTitle>
                  <CardDescription>Tracking endangered and indicator species</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="flex items-center justify-between border-b pb-4">
                      <div>
                        <p className="font-medium">Maned Wolf (Chrysocyon brachyurus)</p>
                        <p className="text-sm text-muted-foreground">Endangered predator</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs bg-amber-100 text-amber-800 px-2 py-1 rounded-full">Returning</span>
                      </div>
                    </div>
                    <div className="flex items-center justify-between border-b pb-4">
                      <div>
                        <p className="font-medium">Giant Anteater (Myrmecophaga tridactyla)</p>
                        <p className="text-sm text-muted-foreground">Vulnerable species</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs bg-red-100 text-red-800 px-2 py-1 rounded-full">Not observed</span>
                      </div>
                    </div>
                    <div className="flex items-center justify-between border-b pb-4">
                      <div>
                        <p className="font-medium">Hyacinth Macaw (Anodorhynchus hyacinthinus)</p>
                        <p className="text-sm text-muted-foreground">Endangered bird</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded-full">Present</span>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
            <TabsContent value="timelapse" className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle>Recovery Time-lapse</CardTitle>
                  <CardDescription>Visual progression of ecosystem recovery</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="aspect-video bg-muted rounded-md flex items-center justify-center">
                    <div className="text-center">
                      <Activity className="size-10 mx-auto text-muted-foreground" />
                      <p className="text-sm text-muted-foreground mt-2">Time-lapse visualization</p>
                    </div>
                  </div>
                  <div className="flex items-center justify-between mt-4">
                    <div className="text-sm">Feb 2025</div>
                    <div className="relative w-full mx-4">
                      <div className="h-1 w-full bg-muted rounded-full"></div>
                      <div className="absolute left-0 top-0 h-1 w-[23%] bg-primary rounded-full"></div>
                    </div>
                    <div className="text-sm">Est. Aug 2028</div>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
            <TabsContent value="interventions" className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle>Recovery Interventions</CardTitle>
                  <CardDescription>Active restoration measures</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="flex items-start gap-4 border-b pb-4">
                      <div className="bg-primary/10 p-2 rounded-full">
                        <Leaf className="size-5 text-primary" />
                      </div>
                      <div>
                        <p className="font-medium">Native Seedling Planting</p>
                        <p className="text-sm text-muted-foreground">12,500 seedlings planted in severely damaged areas</p>
                        <div className="flex items-center gap-2 mt-1">
                          <Progress value={40} className="h-2 w-24" />
                          <span className="text-xs text-muted-foreground">40% complete</span>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-start gap-4 border-b pb-4">
                      <div className="bg-blue-500/10 p-2 rounded-full">
                        <Activity className="size-5 text-blue-500" />
                      </div>
                      <div>
                        <p className="font-medium">Erosion Control Measures</p>
                        <p className="text-sm text-muted-foreground">Installation of erosion barriers on steep slopes</p>
                        <div className="flex items-center gap-2 mt-1">
                          <Progress value={75} className="h-2 w-24" />
                          <span className="text-xs text-muted-foreground">75% complete</span>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-start gap-4">
                      <div className="bg-amber-500/10 p-2 rounded-full">
                        <Activity className="size-5 text-amber-500" />
                      </div>
                      <div>
                        <p className="font-medium">Wildlife Corridors</p>
                        <p className="text-sm text-muted-foreground">Establishing connectivity between unburned patches</p>
                        <div className="flex items-center gap-2 mt-1">
                          <Progress value={25} className="h-2 w-24" />
                          <span className="text-xs text-muted-foreground">25% complete</span>
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
