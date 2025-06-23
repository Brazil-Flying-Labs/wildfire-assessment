import Image from 'next/image'
import { Container } from '@/components/ui/container'
import { ArrowRight, Target, Users, Leaf } from 'lucide-react'

export function Benefits() {
  return (
    <section id="our-vision" className="py-20">
      <Container>
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold tracking-tight mb-4">
            Our Vision for Impact
          </h2>
          <p className="text-xl text-muted-foreground max-w-3xl mx-auto">
            As our partnership begins, we&apos;re setting ambitious goals to make a meaningful difference in Amazon rainforest conservation.
          </p>
        </div>

        {/* Vision Card */}
        <div className="bg-muted/30 border border-border rounded-xl p-6 md:p-8 mb-16">
          <div className="grid md:grid-cols-2 gap-8 items-center">
            <div>
              <div className="inline-block bg-primary/10 text-primary font-medium px-3 py-1 rounded-full text-sm mb-4">
                Partnership Goals
              </div>
              <h3 className="text-2xl md:text-3xl font-bold tracking-tight mb-4">
                A New Collaborative Approach
              </h3>
              <p className="text-muted-foreground mb-6">
                Brazil Flying Labs and Boone Voyage are joining forces to address the critical challenges of fire damage assessment and recovery monitoring in the Amazon rainforest. This partnership combines local expertise with advanced technology to create innovative solutions.
              </p>
              <div className="flex flex-wrap gap-3">
                <span className="bg-background border border-border px-3 py-1 rounded-full text-sm">Launching 2025</span>
                <span className="bg-background border border-border px-3 py-1 rounded-full text-sm">Initial 3-year commitment</span>
                <span className="bg-background border border-border px-3 py-1 rounded-full text-sm">Focus on São Paulo state</span>
              </div>
            </div>
            <div className="relative aspect-video overflow-hidden rounded-lg">
              <Image
                src="/conservation-team.jpg"
                alt="Conservation team planning session"
                fill
                className="object-cover"
              />
              <div className="absolute inset-0 bg-gradient-to-tr from-primary/20 to-transparent" />
            </div>
          </div>
        </div>

        {/* Key Focus Areas */}
        <h3 className="text-2xl font-bold tracking-tight mb-8 text-center">Key Focus Areas</h3>
        <div className="grid md:grid-cols-3 gap-8 mb-16">
          {/* Focus Area 1 */}
          <div className="bg-background border border-border rounded-xl p-6 hover:shadow-md transition-shadow">
            <div className="bg-primary/10 p-3 rounded-full w-12 h-12 flex items-center justify-center mb-4">
              <Target className="text-primary w-6 h-6" />
            </div>
            <h4 className="text-xl font-semibold mb-3">Fire Damage Assessment</h4>
            <p className="text-muted-foreground mb-4">
              Developing advanced methodologies to accurately assess wildfire damage using satellite imagery, drone surveys, and AI analysis.
            </p>
            <ul className="space-y-2 mb-4">
              <li className="flex items-start gap-2">
                <ArrowRight className="text-primary w-4 h-4 mt-1 shrink-0" />
                <span className="text-sm">NDVI and NBR analysis for vegetation health</span>
              </li>
              <li className="flex items-start gap-2">
                <ArrowRight className="text-primary w-4 h-4 mt-1 shrink-0" />
                <span className="text-sm">Drone validation of satellite data</span>
              </li>
              <li className="flex items-start gap-2">
                <ArrowRight className="text-primary w-4 h-4 mt-1 shrink-0" />
                <span className="text-sm">Severity classification models</span>
              </li>
            </ul>
          </div>

          {/* Focus Area 2 */}
          <div className="bg-background border border-border rounded-xl p-6 hover:shadow-md transition-shadow">
            <div className="bg-primary/10 p-3 rounded-full w-12 h-12 flex items-center justify-center mb-4">
              <Leaf className="text-primary w-6 h-6" />
            </div>
            <h4 className="text-xl font-semibold mb-3">Recovery Monitoring</h4>
            <p className="text-muted-foreground mb-4">
              Tracking ecosystem recovery over time to guide restoration efforts and measure the effectiveness of interventions.
            </p>
            <ul className="space-y-2 mb-4">
              <li className="flex items-start gap-2">
                <ArrowRight className="text-primary w-4 h-4 mt-1 shrink-0" />
                <span className="text-sm">Long-term vegetation regrowth tracking</span>
              </li>
              <li className="flex items-start gap-2">
                <ArrowRight className="text-primary w-4 h-4 mt-1 shrink-0" />
                <span className="text-sm">Biodiversity recovery assessment</span>
              </li>
              <li className="flex items-start gap-2">
                <ArrowRight className="text-primary w-4 h-4 mt-1 shrink-0" />
                <span className="text-sm">Ecosystem health indicators</span>
              </li>
            </ul>
          </div>

          {/* Focus Area 3 */}
          <div className="bg-background border border-border rounded-xl p-6 hover:shadow-md transition-shadow">
            <div className="bg-primary/10 p-3 rounded-full w-12 h-12 flex items-center justify-center mb-4">
              <Users className="text-primary w-6 h-6" />
            </div>
            <h4 className="text-xl font-semibold mb-3">Community Engagement</h4>
            <p className="text-muted-foreground mb-4">
              Empowering local communities with tools and training to participate in conservation monitoring and decision-making.
            </p>
            <ul className="space-y-2 mb-4">
              <li className="flex items-start gap-2">
                <ArrowRight className="text-primary w-4 h-4 mt-1 shrink-0" />
                <span className="text-sm">Drone pilot training programs</span>
              </li>
              <li className="flex items-start gap-2">
                <ArrowRight className="text-primary w-4 h-4 mt-1 shrink-0" />
                <span className="text-sm">Data interpretation workshops</span>
              </li>
              <li className="flex items-start gap-2">
                <ArrowRight className="text-primary w-4 h-4 mt-1 shrink-0" />
                <span className="text-sm">Collaborative research initiatives</span>
              </li>
            </ul>
          </div>
        </div>
      </Container>
    </section>
  )
}
