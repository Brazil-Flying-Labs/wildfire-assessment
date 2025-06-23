import { Header } from '@/components/marketing/header'
import { Hero } from '@/components/marketing/hero'
import { Features } from '@/components/marketing/features'
import { Benefits } from '@/components/marketing/benefits'
import { HowItWorks } from '@/components/marketing/how-it-works'
import { CTA } from '@/components/marketing/cta'
import { Contact } from '@/components/marketing/contact'
import { Footer } from '@/components/marketing/footer'

export default function Home() {
  return (
    <div className="flex min-h-screen flex-col">
      <Header />
      <main className="flex-1">
        <Hero />
        <Features />
        <Benefits />
        <HowItWorks />
        <CTA />
        <Contact />
      </main>
      <Footer />
    </div>
  )
}
