import Image from 'next/image'
import Link from 'next/link'
import { Container } from '@/components/ui/container'

export function Hero() {
  return (
    <section className="relative overflow-hidden py-20 md:py-32">
      {/* Background gradient */}
      <div className="absolute inset-0 bg-gradient-to-b from-green-50 to-transparent dark:from-green-950/20 dark:to-background" />
      
      <Container className="relative">
        <div className="grid gap-10 md:grid-cols-2 md:gap-16 items-center">
          <div className="flex flex-col gap-6">
            <div className="flex items-center gap-4 mb-2">
              <div className="bg-background p-1 rounded-md shadow-sm">
                <Image
                  src="/bfl-logo.jpeg"
                  alt="Brazil Flying Labs Logo"
                  width={48}
                  height={48}
                />
              </div>
              <span className="text-primary font-medium">×</span>
              <div className="bg-background p-1 rounded-md shadow-sm">
                <Image
                  src="/boone-voyage-logo.jpeg"
                  alt="Boone Voyage Logo"
                  width={48}
                  height={48}
                />
              </div>
            </div>
            <h1 className="text-4xl md:text-6xl font-bold tracking-tight">
              Uniting Technology & Expertise to <span className="text-primary">Protect the Forest</span>
            </h1>
            <p className="text-xl text-muted-foreground">
              A non-profit collaboration between Brazil Flying Labs and Boone Voyage, using drone technology 
              and AI to assess fire damage, guide recovery efforts, and empower local communities.
            </p>
            <div className="mt-2 text-sm text-muted-foreground bg-muted/50 p-3 rounded-lg border border-border">
              <strong className="text-foreground">The Amazon Crisis:</strong> Over 10,000 square kilometers of rainforest were lost in 2023 alone. Our work is to assess and assist in the restoration of this vital ecosystem.
            </div>
            <div className="flex flex-col sm:flex-row gap-4 mt-4">
              <Link 
                href="#support" 
                className="inline-flex h-11 items-center justify-center rounded-full bg-primary px-8 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
              >
                Support Our Work
              </Link>
              <Link 
                href="#our-story" 
                className="inline-flex h-11 items-center justify-center rounded-full border border-input bg-background px-8 text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground"
              >
                Our Story
              </Link>
            </div>
          </div>
          <div className="relative aspect-video md:aspect-square overflow-hidden rounded-lg">
            <Image
              src="/rainforest-satellite.png"
              alt="Aerial view of the Amazon rainforest"
              fill
              className="object-cover"
              priority
            />
            <div className="absolute inset-0 bg-gradient-to-tr from-primary/20 to-transparent" />
            <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/70 to-transparent p-4 text-white text-sm">
              Aerial view of Jataí Park
            </div>
          </div>
        </div>
      </Container>
    </section>
  )
}
