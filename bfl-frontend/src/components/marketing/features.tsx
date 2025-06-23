import { Satellite, Users, Map, Code, GraduationCap, Leaf } from 'lucide-react'
import { Container } from '@/components/ui/container'

export function Features() {
  return (
    <section id="our-approach" className="py-20 bg-muted/50">
      <Container>
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold tracking-tight mb-4">
            Our Approach to Conservation & Community Empowerment
          </h2>
          <p className="text-xl text-muted-foreground max-w-3xl mx-auto">
            Brazil Flying Labs empowers communities with technology skills while promoting environmental sustainability through innovative drone applications.
          </p>
        </div>
        
        <div className="grid gap-8 md:grid-cols-2 lg:grid-cols-3">
          {/* Approach 1 */}
          <div className="bg-background rounded-lg p-6 shadow-sm border border-border">
            <div className="h-12 w-12 flex items-center justify-center rounded-full bg-primary/10 mb-6">
              <Satellite className="h-6 w-6 text-primary" />
            </div>
            <h3 className="text-xl font-semibold mb-2">Forest Conservation Mapping</h3>
            <p className="text-muted-foreground">
              We collaborate with organizations like the Forest Foundation to map the Atlantic Forest using drone technology, creating detailed orthomosaics and 3D models to support conservation efforts.
            </p>
            <div className="mt-4 text-sm text-primary font-medium">
              Recent project: Mapping biodiversity in the Atlantic Forest region
            </div>
          </div>
          
          {/* Approach 2 */}
          <div className="bg-background rounded-lg p-6 shadow-sm border border-border">
            <div className="h-12 w-12 flex items-center justify-center rounded-full bg-primary/10 mb-6">
              <GraduationCap className="h-6 w-6 text-primary" />
            </div>
            <h3 className="text-xl font-semibold mb-2">STEM Education for Youth</h3>
            <p className="text-muted-foreground">
              We provide hands-on training programs for young people, particularly from underrepresented communities, teaching them drone technology, programming, and environmental monitoring skills.
            </p>
            <div className="mt-4 text-sm text-primary font-medium">
              Impact: Programs in Jundiaí and Cajamar for vulnerable youth
            </div>
          </div>
          
          {/* Approach 3 */}
          <div className="bg-background rounded-lg p-6 shadow-sm border border-border">
            <div className="h-12 w-12 flex items-center justify-center rounded-full bg-primary/10 mb-6">
              <Users className="h-6 w-6 text-primary" />
            </div>
            <h3 className="text-xl font-semibold mb-2">Women in Technology</h3>
            <p className="text-muted-foreground">
              We partner with initiatives like UFABC para MiN@s to increase female participation in STEM fields, offering workshops and competitions that introduce girls to drone technology and robotics.
            </p>
            <div className="mt-4 text-sm text-primary font-medium">
              Achievement: Engaged 30+ girls in recent drone piloting workshops
            </div>
          </div>
          
          {/* Approach 4 */}
          <div className="bg-background rounded-lg p-6 shadow-sm border border-border">
            <div className="h-12 w-12 flex items-center justify-center rounded-full bg-primary/10 mb-6">
              <Code className="h-6 w-6 text-primary" />
            </div>
            <h3 className="text-xl font-semibold mb-2">Python Programming with Drones</h3>
            <p className="text-muted-foreground">
              Our innovative curriculum combines Python programming with drone technology, giving students practical skills that are in high demand while addressing real-world environmental challenges.
            </p>
            <div className="mt-4 text-sm text-primary font-medium">
              Program: Supported by Iron Mountain&apos;s Moving Mountains initiative
            </div>
          </div>
          
          {/* Approach 5 */}
          <div className="bg-background rounded-lg p-6 shadow-sm border border-border">
            <div className="h-12 w-12 flex items-center justify-center rounded-full bg-primary/10 mb-6">
              <Map className="h-6 w-6 text-primary" />
            </div>
            <h3 className="text-xl font-semibold mb-2">Environmental Monitoring</h3>
            <p className="text-muted-foreground">
              We develop drone-based solutions for monitoring and protecting natural habitats, creating detailed maps and data that help communities and organizations make informed conservation decisions.
            </p>
            <div className="mt-4 text-sm text-primary font-medium">
              Focus: Mata Atlântica (Atlantic Forest) preservation efforts
            </div>
          </div>
          
          {/* Approach 6 */}
          <div className="bg-background rounded-lg p-6 shadow-sm border border-border">
            <div className="h-12 w-12 flex items-center justify-center rounded-full bg-primary/10 mb-6">
              <Leaf className="h-6 w-6 text-primary" />
            </div>
            <h3 className="text-xl font-semibold mb-2">Sustainable Agriculture</h3>
            <p className="text-muted-foreground">
              We support farmers with drone technology to increase crop yields while promoting sustainable practices, helping to reduce the pressure on natural forests while improving food security.
            </p>
            <div className="mt-4 text-sm text-primary font-medium">
              Vision: Supporting São Paulo state farmers with aerial monitoring
            </div>
          </div>
        </div>
      </Container>
    </section>
  )
}
