import Image from 'next/image'
import { Container } from '@/components/ui/container'

export function HowItWorks() {
  return (
    <section id="our-story" className="py-20 bg-muted/50">
      <Container>
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold tracking-tight mb-4">
            Our Collaborative Journey
          </h2>
          <p className="text-xl text-muted-foreground max-w-3xl mx-auto">
            How Brazil Flying Labs and Boone Voyage came together to create a unique partnership that combines local expertise with technological innovation.
          </p>
        </div>
        
        <div className="relative">
          {/* Connection line */}
          <div className="absolute left-1/2 top-0 bottom-0 w-0.5 bg-border -translate-x-1/2 hidden md:block" />
          
          {/* Phase 1 */}
          <div className="grid md:grid-cols-2 gap-8 mb-16 relative">
            <div className="md:text-right md:pr-16">
              <div className="bg-primary text-primary-foreground w-8 h-8 rounded-full flex items-center justify-center font-bold mb-4 md:ml-auto">1</div>
              <h3 className="text-2xl font-semibold mb-3">Partnership Formation</h3>
              <p className="text-muted-foreground">
                In 2025, Brazil Flying Labs, with their expertise in STEM education, drone mapping, and community empowerment, is joining forces with Boone Voyage, specialists in AI and satellite imagery analysis. Together, we&apos;ve identified opportunities to apply drone technology to environmental conservation in the Amazon.
              </p>
              <div className="bg-background p-3 rounded-lg border border-border mt-4 md:text-left">
                <div className="flex items-center gap-2 mb-2">
                  <div className="bg-primary/10 p-1 rounded-md">
                    <Image src="/bfl-logo.svg" alt="Brazil Flying Labs" width={20} height={20} />
                  </div>
                  <span className="font-medium">Brazil Flying Labs contributes:</span>
                </div>
                <ul className="list-disc pl-6 text-muted-foreground text-sm space-y-1">
                  <li>Expertise in drone mapping for conservation</li>
                  <li>STEM education and community engagement</li>
                  <li>Experience with Atlantic Forest preservation</li>
                </ul>
              </div>
            </div>
            <div className="relative aspect-video rounded-lg overflow-hidden md:order-first md:mt-12">
              <Image
                src="/partnership-formation.jpg"
                alt="Brazil Flying Labs and Boone Voyage teams meeting"
                fill
                className="object-cover"
              />
            </div>
            {/* Connection dot */}
            <div className="absolute left-1/2 top-1/2 w-4 h-4 bg-primary rounded-full -translate-x-1/2 -translate-y-1/2 hidden md:block" />
          </div>
          
          {/* Phase 2 */}
          <div className="grid md:grid-cols-2 gap-8 mb-16 relative">
            <div className="md:pl-16">
              <div className="bg-primary text-primary-foreground w-8 h-8 rounded-full flex items-center justify-center font-bold mb-4">2</div>
              <h3 className="text-2xl font-semibold mb-3">Community-Centered Design</h3>
              <p className="text-muted-foreground">
                Building on Brazil Flying Labs&apos; successful community-centered approach, we&apos;re designing programs that empower local communities through technology education while addressing environmental challenges. This approach has proven effective in their work with youth in São Paulo state.
              </p>
              <div className="bg-background p-3 rounded-lg border border-border mt-4">
                <div className="flex items-center gap-2 mb-2">
                  <div className="bg-primary/10 p-1 rounded-md">
                    <Image src="/boone-voyage-logo.svg" alt="Boone Voyage" width={20} height={20} />
                  </div>
                  <span className="font-medium">Boone Voyage contributes:</span>
                </div>
                <ul className="list-disc pl-6 text-muted-foreground text-sm space-y-1">
                  <li>AI and machine learning expertise</li>
                  <li>Satellite imagery analysis</li>
                  <li>Software development resources</li>
                </ul>
              </div>
            </div>
            <div className="relative aspect-video rounded-lg overflow-hidden md:mt-12">
              <Image
                src="/community-engagement.jpg"
                alt="Team meeting with local community members"
                fill
                className="object-cover"
              />
            </div>
            {/* Connection dot */}
            <div className="absolute left-1/2 top-1/2 w-4 h-4 bg-primary rounded-full -translate-x-1/2 -translate-y-1/2 hidden md:block" />
          </div>
          
          {/* Phase 3 */}
          <div className="grid md:grid-cols-2 gap-8 mb-16 relative">
            <div className="md:text-right md:pr-16">
              <div className="bg-primary text-primary-foreground w-8 h-8 rounded-full flex items-center justify-center font-bold mb-4 md:ml-auto">3</div>
              <h3 className="text-2xl font-semibold mb-3">Technology & Education Integration</h3>
              <p className="text-muted-foreground">
                Our approach combines Brazil Flying Labs&apos; expertise in drone mapping and environmental monitoring with educational initiatives that teach programming and technology skills. This integrated approach has proven successful in their Atlantic Forest mapping projects and youth education programs.
              </p>
              <blockquote className="border-l-4 border-primary pl-4 italic text-muted-foreground mt-4 md:text-left">
              &quot;We&apos;re not just teaching them to code; we&apos;re showing them how technology can address real-world challenges, including those within their own communities.&quot;
                <footer className="mt-2 font-medium text-foreground">— Brazil Flying Labs team</footer>
              </blockquote>
            </div>
            <div className="relative aspect-video rounded-lg overflow-hidden md:order-first md:mt-12">
              <Image
                src="/field-operations.jpg"
                alt="Drone mapping operation for environmental monitoring"
                fill
                className="object-cover"
              />
            </div>
            {/* Connection dot */}
            <div className="absolute left-1/2 top-1/2 w-4 h-4 bg-primary rounded-full -translate-x-1/2 -translate-y-1/2 hidden md:block" />
          </div>
          
          {/* Phase 4 */}
          <div className="grid md:grid-cols-2 gap-8 relative">
            <div className="md:pl-16">
              <div className="bg-primary text-primary-foreground w-8 h-8 rounded-full flex items-center justify-center font-bold mb-4">4</div>
              <h3 className="text-2xl font-semibold mb-3">Looking Forward</h3>
              <p className="text-muted-foreground">
                As our partnership evolves, we&apos;re expanding our impact through several key initiatives that build on Brazil Flying Labs&apos; successful programs in STEM education, women in technology, and environmental monitoring through drone technology.
              </p>
              <div className="bg-muted/70 p-3 rounded-lg mt-4">
                <h4 className="font-medium mb-2 text-sm">2025-2026 Goals:</h4>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div className="bg-background p-2 rounded border border-border">
                    <div className="font-medium">3</div>
                    <div className="text-muted-foreground">Forest areas mapped</div>
                  </div>
                  <div className="bg-background p-2 rounded border border-border">
                    <div className="font-medium">50</div>
                    <div className="text-muted-foreground">Youth trained in technology</div>
                  </div>
                  <div className="bg-background p-2 rounded border border-border">
                    <div className="font-medium">2</div>
                    <div className="text-muted-foreground">Educational programs launched</div>
                  </div>
                  <div className="bg-background p-2 rounded border border-border">
                    <div className="font-medium">1</div>
                    <div className="text-muted-foreground">Conservation data platform</div>
                  </div>
                </div>
              </div>
            </div>
            <div className="relative aspect-video rounded-lg overflow-hidden md:mt-12">
              <Image
                src="/future-vision.jpg"
                alt="Team planning future initiatives"
                fill
                className="object-cover"
              />
            </div>
            {/* Connection dot */}
            <div className="absolute left-1/2 top-1/2 w-4 h-4 bg-primary rounded-full -translate-x-1/2 -translate-y-1/2 hidden md:block" />
          </div>
        </div>
      </Container>
    </section>
  )
}
