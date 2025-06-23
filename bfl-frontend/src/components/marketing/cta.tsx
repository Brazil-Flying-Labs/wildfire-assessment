"use client"
import { Container } from '@/components/ui/container'
import {  Heart, Share2 } from 'lucide-react'

export function CTA() {
  return (
    <section id="join-us" className="py-20 bg-primary/10">
      <Container>
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-3xl md:text-4xl font-bold tracking-tight mb-6">
            Join Our Mission to Protect the Amazon
          </h2>
          <p className="text-xl text-muted-foreground mb-8 max-w-2xl mx-auto">
            Together, Brazil Flying Labs and Boone Voyage are empowering communities and restoring ecosystems. Your support can help us expand our impact across the Amazon region.
          </p>
          
          <div className="grid md:grid-cols-2 gap-8 mb-10 max-w-2xl mx-auto">
            <div className="bg-background rounded-lg p-8 shadow-sm text-center">
              <div className="bg-primary/10 p-3 rounded-full w-12 h-12 flex items-center justify-center mb-4 mx-auto">
                <Heart className="text-primary w-6 h-6" />
              </div>
              <h3 className="text-xl font-semibold mb-3">Donate</h3>
              <p className="text-muted-foreground mb-6">Support our conservation efforts through donations that directly fund our field operations, technology, and community programs.</p>
              <a 
                href="https://flyinglabs.org/contact-us" 
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex h-10 items-center justify-center rounded-full bg-primary px-6 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
              >
                Donate Now
              </a>
            </div>
            
            <div className="bg-background rounded-lg p-8 shadow-sm text-center">
              <div className="bg-primary/10 p-3 rounded-full w-12 h-12 flex items-center justify-center mb-4 mx-auto">
                <Share2 className="text-primary w-6 h-6" />
              </div>
              <h3 className="text-xl font-semibold mb-3">Share</h3>
              <p className="text-muted-foreground mb-6">Help spread awareness about our work and the importance of rainforest conservation through your social networks.</p>
              <div className="flex justify-center gap-4">
                <a 
                  href="https://twitter.com/intent/tweet?text=Join%20Brazil%20Flying%20Labs%20and%20Boone%20Voyage%20in%20protecting%20the%20Amazon%20rainforest%20through%20innovative%20technology%20and%20community%20engagement." 
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex h-10 items-center justify-center rounded-full border border-input bg-background px-4 text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground"
                >
                  Twitter
                </a>
                <a 
                  href="https://www.facebook.com/sharer/sharer.php?u=https://amazon-rainforest-initiative.org" 
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex h-10 items-center justify-center rounded-full border border-input bg-background px-4 text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground"
                >
                  Facebook
                </a>
                <a 
                  href="https://www.linkedin.com/sharing/share-offsite/?url=https://amazon-rainforest-initiative.org" 
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex h-10 items-center justify-center rounded-full border border-input bg-background px-4 text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground"
                >
                  LinkedIn
                </a>
              </div>
            </div>
          </div>
        </div>
      </Container>
    </section>
  )
}
